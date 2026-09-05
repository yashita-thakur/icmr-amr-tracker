"""V3 -- the cross-network comparability matrix.

The matrix answers one question per cell: which network reports this organism x
antibiotic x year, on which metric, from which specimen basis. It must never
answer a second one. AMRSN publishes % susceptible, NARS-Net publishes
% resistant, and AMRSN publishes no % intermediate for either organism, so an
AMRSN % resistant cannot be computed and the two series share no comparison
value. A matrix carrying values would be exactly the join that must not exist.

So the first group of tests below is not about correctness of counts -- it is
about that guarantee holding structurally, in both directions: the real
exported payload carries no value, and the guard actually fires when one is
planted. The rest pin the coverage arithmetic and the two facts most likely to
be got wrong by a later reader: that panel-level overlap is not cell-level
overlap, and that the two organisms' AMRSN specimen bases are not the same.
"""

from __future__ import annotations

import json

import pytest

from src.build_comparability import (
    AMRSN,
    AMRSN_SPECIMEN_BASIS,
    COVERAGE_AMRSN_ONLY,
    COVERAGE_BOTH,
    COVERAGE_NARSNET_ONLY,
    COVERAGE_NEITHER,
    NARSNET,
    ORGANISMS,
    PERCENT_RESISTANT,
    PERCENT_SUSCEPTIBLE,
    VALUE_FIELDS,
    YEARS,
    ValueLeakError,
    amrsn_coverage,
    assert_carries_no_values,
    build_matrix,
    export,
    load_amrsn_rows,
    load_narsnet_rows,
    summarise,
)
from src.parsers.base import FIELDNAMES as AMRSN_FIELDNAMES
from src.parsers.narsnet_parser import NARSNET_FIELDNAMES

# Fields in either row schema that identify a cell, describe its provenance or
# record a status -- everything that is NOT a surveillance value. Kept here
# rather than in the module so that adding a field to either schema without
# classifying it fails a test instead of silently widening what may be copied
# into the matrix.
NON_VALUE_FIELDS = {
    "network",
    "organism",
    "antibiotic",
    "specimen",
    "year",
    "numerator_status",
    "reconcilable",
    "source_report_year",
    "source_cover_year",
    "source_table",
    "source_url",
    "extracted_date",
    "flags",
}


@pytest.fixture(scope="module")
def matrix():
    amrsn = amrsn_coverage(load_amrsn_rows())
    from src.build_comparability import narsnet_coverage

    narsnet = narsnet_coverage(load_narsnet_rows())
    cells = build_matrix(amrsn, narsnet)
    return cells, summarise(cells)


@pytest.fixture(scope="module")
def payload(matrix, tmp_path_factory):
    cells, summary = matrix
    path = export(cells, summary, path=tmp_path_factory.mktemp("cmp") / "m.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# The guarantee: no value from either network reaches the matrix
# ---------------------------------------------------------------------------


def test_value_fields_covers_every_value_bearing_field_in_both_schemas():
    """A new schema field must be classified, not silently allowed through."""
    all_fields = set(AMRSN_FIELDNAMES) | set(NARSNET_FIELDNAMES)
    unclassified = all_fields - NON_VALUE_FIELDS - set(VALUE_FIELDS)
    assert unclassified == set(), (
        "field(s) in a row schema are neither declared non-value in this test "
        "nor listed in VALUE_FIELDS: {}".format(sorted(unclassified))
    )


def test_exported_payload_carries_no_value(payload):
    assert_carries_no_values(payload)


def test_no_value_field_name_appears_at_any_depth(payload):
    seen = set()

    def walk(node):
        if isinstance(node, dict):
            seen.update(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(payload)
    assert seen & set(VALUE_FIELDS) == set()


def test_guard_fires_on_a_planted_value_field():
    with pytest.raises(ValueLeakError, match="value-bearing field"):
        assert_carries_no_values({"matrix": [{"amrsn": {"susceptible_pct": 42}}]})


def test_guard_fires_on_a_planted_float_under_an_innocent_key():
    """A percentage smuggled in under a name VALUE_FIELDS does not know."""
    with pytest.raises(ValueLeakError, match="is a float"):
        assert_carries_no_values({"matrix": [{"amrsn": {"headline": 42.4}}]})


def test_guard_reports_where_the_value_leaked(payload):
    bad = dict(payload)
    bad["matrix"] = [{"narsnet": {"resistant_pct": 29}}]
    with pytest.raises(ValueLeakError, match=r"matrix\[0\]\.narsnet\.resistant_pct"):
        assert_carries_no_values(bad)


def test_years_are_integers_not_floats(payload):
    """The float guard is only meaningful if legitimate numbers are ints."""
    years = {cell["year"] for cell in payload["matrix"]}
    assert years == set(YEARS)
    assert all(isinstance(y, int) for y in years)


# ---------------------------------------------------------------------------
# Coverage classification
# ---------------------------------------------------------------------------


def _entry(metric):
    return {"metric": metric, "specimen_basis": "x", "sources": []}


@pytest.mark.parametrize(
    "in_amrsn,in_narsnet,expected",
    [
        (True, True, COVERAGE_BOTH),
        (False, True, COVERAGE_NARSNET_ONLY),
        (True, False, COVERAGE_AMRSN_ONLY),
    ],
)
def test_coverage_state_for_each_combination(in_amrsn, in_narsnet, expected):
    key = ("Escherichia coli", "meropenem", 2021)
    amrsn = {key: _entry(PERCENT_SUSCEPTIBLE)} if in_amrsn else {}
    narsnet = {key: _entry(PERCENT_RESISTANT)} if in_narsnet else {}
    cells = build_matrix(
        amrsn, narsnet, organisms=["Escherichia coli"], years=[2021]
    )
    assert len(cells) == 1
    assert cells[0]["coverage"] == expected
    assert (cells[0][AMRSN] is not None) is in_amrsn
    assert (cells[0][NARSNET] is not None) is in_narsnet


def test_a_drug_neither_network_reports_is_not_a_row_at_all():
    """The row set is the union of the two panels, not a fixed drug list. So
    'neither' is never a whole row -- it is a year inside a row some network
    does report, which is what the blank squares in the figure mean."""
    cells = build_matrix({}, {}, organisms=["Escherichia coli"], years=[2021])
    assert cells == []


def test_a_neither_cell_carries_no_network_object():
    key = ("Escherichia coli", "meropenem", 2021)
    cells = build_matrix(
        {key: _entry(PERCENT_SUSCEPTIBLE)},
        {},
        organisms=["Escherichia coli"],
        years=[2021, 2022],
    )
    neither = [c for c in cells if c["year"] == 2022][0]
    assert neither["coverage"] == COVERAGE_NEITHER
    assert neither[AMRSN] is None and neither[NARSNET] is None


def test_matrix_is_rectangular_and_each_key_appears_once(matrix):
    cells, summary = matrix
    keys = [(c["organism"], c["antibiotic"], c["year"]) for c in cells]
    assert len(keys) == len(set(keys))
    for entry in summary["by_organism"]:
        assert entry["cells"] == entry["antibiotic_count"] * len(YEARS)
    assert summary["cells"] == sum(e["cells"] for e in summary["by_organism"])


# ---------------------------------------------------------------------------
# The counts, pinned
# ---------------------------------------------------------------------------


def test_matrix_shape_and_coverage_counts(matrix):
    _cells, summary = matrix
    by_organism = {e["organism"]: e for e in summary["by_organism"]}
    assert sorted(by_organism) == sorted(ORGANISMS)

    ec = by_organism["Escherichia coli"]
    assert ec["antibiotic_count"] == 21
    assert ec["cells"] == 168
    assert ec["coverage_counts"] == {
        COVERAGE_BOTH: 45,
        COVERAGE_NARSNET_ONLY: 56,
        COVERAGE_AMRSN_ONLY: 35,
        COVERAGE_NEITHER: 32,
    }

    sa = by_organism["Staphylococcus aureus"]
    assert sa["antibiotic_count"] == 13
    assert sa["cells"] == 104
    assert sa["coverage_counts"] == {
        COVERAGE_BOTH: 55,
        COVERAGE_NARSNET_ONLY: 16,
        COVERAGE_AMRSN_ONLY: 33,
        # Every S. aureus drug either network prints is printed by one of them
        # in all eight years, so this organism's grid has no blank square.
        COVERAGE_NEITHER: 0,
    }

    assert summary["cells"] == 272
    assert summary["coverage_counts"] == {
        COVERAGE_BOTH: 100,
        COVERAGE_NARSNET_ONLY: 72,
        COVERAGE_AMRSN_ONLY: 68,
        COVERAGE_NEITHER: 32,
    }


def test_panel_overlap_matches_the_investigation(matrix):
    """The overlap counts recorded in docs/narsnet_v3_research.md B3."""
    _cells, summary = matrix
    by_organism = {e["organism"]: e for e in summary["by_organism"]}

    ec = by_organism["Escherichia coli"]
    assert ec["antibiotics_both_networks_report"] == [
        "amikacin",
        "cefotaxime",
        "ceftazidime",
        "ciprofloxacin",
        "ertapenem",
        "imipenem",
        "meropenem",
        "piperacillin-tazobactam",
    ]
    # Never in any NARS-Net E. coli panel, in any of the eight editions.
    assert ec["antibiotics_amrsn_only"] == ["cefazolin", "levofloxacin"]

    sa = by_organism["Staphylococcus aureus"]
    assert len(sa["antibiotics_both_networks_report"]) == 9
    assert sa["antibiotics_narsnet_only"] == ["doxycycline", "gentamicin"]
    # Oxacillin never appears as a row in any NARS-Net edition; cefoxitin is
    # the sole MRSA surrogate throughout.
    assert sa["antibiotics_amrsn_only"] == ["oxacillin", "tigecycline"]


def test_ceftazidime_is_shared_at_panel_level_but_overlaps_in_one_year_only(matrix):
    """Panel-level overlap is not cell-level overlap, and the two must not be
    read off each other. Ceftazidime is in the AMRSN panel every year and in a
    NARS-Net E. coli table only in 2017."""
    cells, summary = matrix
    ec = [e for e in summary["by_organism"] if e["organism"] == "Escherichia coli"][0]
    assert "ceftazidime" in ec["antibiotics_both_networks_report"]

    own = [
        c
        for c in cells
        if c["organism"] == "Escherichia coli" and c["antibiotic"] == "ceftazidime"
    ]
    both = [c for c in own if c["coverage"] == COVERAGE_BOTH]
    assert [c["year"] for c in both] == [2017]
    assert all(c["coverage"] == COVERAGE_AMRSN_ONLY for c in own if c["year"] != 2017)


# ---------------------------------------------------------------------------
# Metric and specimen basis
# ---------------------------------------------------------------------------


def test_the_two_metrics_are_distinct_and_never_swapped(matrix):
    cells, _summary = matrix
    assert PERCENT_SUSCEPTIBLE != PERCENT_RESISTANT
    for cell in cells:
        if cell[AMRSN]:
            assert cell[AMRSN]["metric"] == PERCENT_SUSCEPTIBLE
        if cell[NARSNET]:
            assert cell[NARSNET]["metric"] == PERCENT_RESISTANT


def test_amrsn_specimen_basis_differs_between_the_two_organisms(matrix):
    """Quoted from the captions, checked in all three editions. The E. coli
    table excludes urine; the S. aureus table states no exclusion at all, so
    the mismatch against a NARS-Net stratum is not the same for the two."""
    assert AMRSN_SPECIMEN_BASIS["Escherichia coli"] == (
        "all samples (except faeces and urine)"
    )
    assert AMRSN_SPECIMEN_BASIS["Staphylococcus aureus"] == "all samples"

    cells, _summary = matrix
    for cell in cells:
        if cell[AMRSN]:
            assert cell[AMRSN]["specimen_basis"] == AMRSN_SPECIMEN_BASIS[
                cell["organism"]
            ]


def test_narsnet_specimen_basis_is_the_columns_that_drug_is_printed_in(matrix):
    """Not the edition's full column set. Nitrofurantoin is reported for urine
    only in 2019, with its other specimen blocks greyed out, so its basis is
    the urine column and the pooled column that covers it -- not all four."""
    cells, _summary = matrix
    cell = [
        c
        for c in cells
        if c["organism"] == "Escherichia coli"
        and c["antibiotic"] == "nitrofurantoin"
        and c["year"] == 2019
    ][0]
    assert cell[NARSNET]["specimen_basis"] == [
        "blood+urine+pus_aspirate+osbf",
        "urine",
    ]


def test_composite_specimen_columns_keep_every_constituent(matrix):
    """A composite is never collapsed to a 'pooled' label, because composite
    membership is not the same across editions."""
    cells, _summary = matrix
    cell = [
        c
        for c in cells
        if c["organism"] == "Staphylococcus aureus"
        and c["antibiotic"] == "cefoxitin"
        and c["year"] == 2018
    ][0]
    assert cell[NARSNET]["specimen_basis"] == [
        "blood",
        "blood+pus_aspirate+osbf",
        "pus_aspirate+osbf",
    ]


def test_no_narsnet_cell_from_2021_onward_carries_a_composite_column(matrix):
    """The 2021 edition splits pus aspirate and OSBF and drops every pooled
    column, so no post-2021 column has the same membership as any earlier one."""
    cells, _summary = matrix
    for cell in cells:
        if cell[NARSNET] and cell["year"] >= 2021:
            assert all("+" not in s for s in cell[NARSNET]["specimen_basis"])


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def test_every_narsnet_cell_comes_from_exactly_one_edition(matrix):
    """Each NARS-Net edition reports its own period only -- no edition reprints
    a prior year's table, which is why narsnet_revisions.json is empty."""
    cells, _summary = matrix
    for cell in cells:
        if cell[NARSNET]:
            assert len(cell[NARSNET]["sources"]) == 1
            assert cell[NARSNET]["sources"][0]["report_year"] == cell["year"]


def test_amrsn_cells_are_carried_by_up_to_three_editions(matrix):
    """The retrospective trend tables repeat each calendar year, which is what
    makes cross-edition revision detection possible at all."""
    cells, _summary = matrix
    counts = {
        len(c[AMRSN]["sources"]) for c in cells if c[AMRSN]
    }
    assert counts <= {1, 2, 3}
    assert 3 in counts
    for cell in cells:
        if not cell[AMRSN]:
            continue
        for source in cell[AMRSN]["sources"]:
            assert source["report_year"] >= cell["year"]
            assert source["table"].startswith("Table ")


def test_payload_carries_the_notes_a_reader_needs(payload):
    for key in ("description", "specimen_basis_note", "sources_note", "attribution"):
        assert payload[key].strip()
    assert "no percentage and no count" in payload["description"].lower()
    assert payload["metrics"] == {
        AMRSN: PERCENT_SUSCEPTIBLE,
        NARSNET: PERCENT_RESISTANT,
    }


def test_export_round_trips(matrix, tmp_path):
    cells, summary = matrix
    path = export(cells, summary, generated="test", path=tmp_path / "m.json")
    with open(path, encoding="utf-8") as fh:
        loaded = json.load(fh)
    assert loaded["generated"] == "test"
    assert loaded["matrix"] == cells
    assert loaded["summary"] == summary


def test_export_refuses_to_write_a_payload_carrying_a_value(matrix, tmp_path):
    """The guard runs before the write, so a leak never reaches disk."""
    cells, summary = matrix
    leaky = [dict(cells[0], amrsn={"tested_n": 12445})] + cells[1:]
    path = tmp_path / "m.json"
    with pytest.raises(ValueLeakError):
        export(leaky, summary, path=path)
    assert not path.exists()
