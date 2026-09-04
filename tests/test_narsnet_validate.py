"""V3 validator tests: fixtures, the cross-column checks, and the exports.

The cross-column check is the reason this module exists. A within-cell check
compares a printed percentage against the counts printed beside it and can only
ever see one cell at a time. It cannot see that in the 2019 E. coli table the
pooled column and the urine column print the same denominator for a urine-only
drug and two different numerators. Most of what follows is about keeping that
check narrow enough to mean something.
"""

from __future__ import annotations

import csv
import json

import pytest

from src.narsnet_validate import (
    DEGENERATE_FLAG,
    NARSNET_FIXTURES,
    REVISIONS_NOTE,
    SPECIMEN_COLUMNS_CHANGED_FLAG,
    apply_degenerate_composite_flags,
    apply_narsnet_panel_flags,
    check_narsnet_fixtures,
    detect_narsnet_panel_changes,
    find_degenerate_composite_disagreements,
    find_narsnet_cross_report_revisions,
    internal_consistency,
    narsnet_panel_by_edition,
    summarise_composite_sums,
    summarise_corrupt_numerators,
)
from src.parsers.base import FIELDNAMES as AMRSN_FIELDNAMES
from src.parsers.narsnet_parser import (
    NARSNET_FIELDNAMES,
    NUMERATOR_CORRUPT,
    NUMERATOR_PRINTED,
    NarsNetRecord,
    SPECS,
    parse_narsnet_report,
)
from src.sources import NARSNET_SOURCES, PROCESSED_DIR
from src import build_narsnet_dataset as builder

EC = "Escherichia coli"
SA = "Staphylococcus aureus"
BLOOD = "blood"
URINE = "urine"
PUS_ASPIRATE = "pus_aspirate"
OSBF = "osbf"
PA_OSBF = "pus_aspirate+osbf"
ALL_FOUR = "blood+urine+pus_aspirate+osbf"


def make(organism, antibiotic, specimen, year, tested, resistant, pct):
    return NarsNetRecord(
        network="narsnet",
        organism=organism,
        antibiotic=antibiotic,
        specimen=specimen,
        year=year,
        tested_n=tested,
        resistant_n=resistant,
        resistant_pct=pct,
        numerator_status=NUMERATOR_PRINTED,
        reconcilable=True,
        ci_low=None,
        ci_high=None,
        source_report_year=year,
        source_cover_year=None,
        source_table="Table 1",
        source_url="https://example.invalid/x.pdf",
        extracted_date="test",
        reported_pct=pct,
        computed_pct=None,
    )


# --- unit: the degenerate-composite check -----------------------------------


def test_degenerate_composite_disagreement_is_detected():
    """A composite covering exactly one reported stratum: same isolates, so the
    counts must agree. This is the 2019 nitrofurantoin shape."""
    records = [
        make(EC, "nitrofurantoin", ALL_FOUR, 2019, 16741, 2026, 12.0),
        make(EC, "nitrofurantoin", URINE, 2019, 16741, 2042, 12.0),
    ]
    findings = find_degenerate_composite_disagreements(records)
    assert len(findings) == 1
    f = findings[0]
    assert f["composite_specimen"] == ALL_FOUR
    assert f["only_reported_stratum"] == URINE
    assert f["shared_tested_n"] == 16741
    assert (f["composite_resistant_n"], f["stratum_resistant_n"]) == (2026, 2042)
    assert f["difference"] == -16


def test_degenerate_composite_in_agreement_is_not_reported():
    records = [
        make(EC, "nitrofurantoin", ALL_FOUR, 2019, 16741, 2042, 12.0),
        make(EC, "nitrofurantoin", URINE, 2019, 16741, 2042, 12.0),
    ]
    assert find_degenerate_composite_disagreements(records) == []


def test_a_partitioned_composite_is_not_treated_as_degenerate():
    """Two or more covering columns is a partition, not a restatement. Those
    legitimately differ from their sum and are summarised, never flagged."""
    records = [
        make(EC, "ampicillin", ALL_FOUR, 2019, 14943, 12971, 87.0),
        make(EC, "ampicillin", PA_OSBF, 2019, 2563, 2327, 91.0),
        make(EC, "ampicillin", BLOOD, 2019, 1087, 934, 86.0),
        make(EC, "ampicillin", URINE, 2019, 11293, 9701, 86.0),
    ]
    assert find_degenerate_composite_disagreements(records) == []


def test_a_differing_denominator_is_not_a_degenerate_case():
    """If the denominators differ the two columns are not the same isolates, so
    a numerator difference says nothing and must not be claimed as a finding."""
    records = [
        make(EC, "nitrofurantoin", ALL_FOUR, 2019, 16741, 2026, 12.0),
        make(EC, "nitrofurantoin", URINE, 2019, 16000, 2042, 12.8),
    ]
    assert find_degenerate_composite_disagreements(records) == []


def test_degenerate_flags_land_on_both_sides():
    records = [
        make(EC, "nitrofurantoin", ALL_FOUR, 2019, 16741, 2026, 12.0),
        make(EC, "nitrofurantoin", URINE, 2019, 16741, 2042, 12.0),
    ]
    apply_degenerate_composite_flags(records)
    for r in records:
        assert any(f.startswith(DEGENERATE_FLAG) for f in r.flags)


def test_composite_sums_are_summarised_without_flagging():
    records = [
        make(EC, "ampicillin", ALL_FOUR, 2019, 14943, 12971, 87.0),
        make(EC, "ampicillin", PA_OSBF, 2019, 2563, 2327, 91.0),
        make(EC, "ampicillin", BLOOD, 2019, 1087, 934, 86.0),
        make(EC, "ampicillin", URINE, 2019, 11293, 9701, 86.0),
    ]
    rows = summarise_composite_sums(records)
    assert len(rows) == 1
    assert rows[0]["tested_difference"] == 0
    assert rows[0]["resistant_difference"] == 9
    assert all(not r.flags for r in records), "summarising must not raise a flag"


# --- unit: panel and specimen columns ---------------------------------------


def test_specimen_column_change_is_detected_when_the_drug_panel_is_identical():
    """Between 2019 and 2020 the E. coli drug panel does not change but the
    pooled column disappears. A drug-only comparison would miss it."""
    records = [
        make(EC, "ampicillin", ALL_FOUR, 2019, 10, 5, 50.0),
        make(EC, "ampicillin", BLOOD, 2019, 10, 5, 50.0),
        make(EC, "ampicillin", BLOOD, 2020, 10, 5, 50.0),
    ]
    changes = detect_narsnet_panel_changes(narsnet_panel_by_edition(records))
    assert len(changes) == 1
    assert changes[0]["antibiotics_added"] == []
    assert changes[0]["antibiotics_removed"] == []
    assert changes[0]["specimen_columns_removed"] == [ALL_FOUR]


def test_panel_flags_land_on_the_later_edition_only():
    records = [
        make(EC, "ampicillin", ALL_FOUR, 2019, 10, 5, 50.0),
        make(EC, "ampicillin", BLOOD, 2019, 10, 5, 50.0),
        make(EC, "ampicillin", BLOOD, 2020, 10, 5, 50.0),
    ]
    apply_narsnet_panel_flags(records)
    later = [r for r in records if r.source_report_year == 2020]
    earlier = [r for r in records if r.source_report_year == 2019]
    assert all(
        any(f.startswith(SPECIMEN_COLUMNS_CHANGED_FLAG) for f in r.flags)
        for r in later
    )
    assert all(not r.flags for r in earlier)


# --- unit: revisions --------------------------------------------------------


def test_revisions_are_empty_when_no_key_spans_two_editions():
    records = [
        make(EC, "ampicillin", BLOOD, 2019, 10, 5, 50.0),
        make(EC, "ampicillin", BLOOD, 2020, 10, 6, 60.0),
    ]
    # Different `year` as well as different edition, which is the real shape:
    # a NARS-Net edition only ever reports its own reporting period.
    assert find_narsnet_cross_report_revisions(records) == []


def test_a_real_revision_would_still_be_caught():
    """Empty by design must not mean the check is a no-op. If an edition ever
    did print a retrospective table, this has to start returning rows."""
    a = make(EC, "ampicillin", BLOOD, 2019, 10, 5, 50.0)
    b = make(EC, "ampicillin", BLOOD, 2019, 10, 6, 60.0)
    b.source_report_year = 2020
    assert len(find_narsnet_cross_report_revisions([a, b])) == 1


def test_revisions_note_says_why_it_is_empty():
    assert "BY DESIGN" in REVISIONS_NOTE
    assert "no way to look" in REVISIONS_NOTE


# --- unit: the two datasets must not look concatenable -----------------------


def test_the_two_schemas_share_no_comparison_column():
    """AMRSN carries % susceptible, NARS-Net % resistant. If the two schemas
    ever shared a value column, someone would eventually concatenate them."""
    shared = set(AMRSN_FIELDNAMES) & set(NARSNET_FIELDNAMES)
    assert "susceptible_pct" not in NARSNET_FIELDNAMES
    assert "resistant_pct" not in AMRSN_FIELDNAMES
    # Provenance columns are shared on purpose; measurement columns are not.
    assert shared == {
        "organism", "antibiotic", "year", "source_report_year", "source_table",
        "source_url", "extracted_date", "reported_pct", "computed_pct", "flags",
        "tested_n",
    }


# --- integration -------------------------------------------------------------

_missing = [y for y in (2019, 2020, 2021) if not NARSNET_SOURCES[y].path.exists()]
needs_pdfs = pytest.mark.skipif(
    _missing,
    reason="data/raw/ missing narsnet {}; run "
    "`python -m src.fetch --network narsnet` first".format(_missing),
)


@pytest.fixture(scope="session")
def records():
    recs = []
    for year in (2019, 2020, 2021):
        for organism in SPECS:
            recs.extend(
                parse_narsnet_report(
                    NARSNET_SOURCES[year], SPECS[organism], extracted_date="test"
                )
            )
    return recs


@needs_pdfs
def test_every_fixture_passes(records):
    passes, failures = check_narsnet_fixtures(records)
    assert not failures, "\n".join(failures)
    assert len(passes) == len(NARSNET_FIXTURES)


@needs_pdfs
def test_most_fixtures_are_narrative(records):
    """Prose is written independently of the table, so agreement between them is
    corroboration rather than a tautology."""
    narrative = [fx for fx in NARSNET_FIXTURES if fx.note.startswith("narrative")]
    assert len(narrative) >= len(NARSNET_FIXTURES) // 2


@needs_pdfs
def test_the_2019_nitrofurantoin_disagreement_is_the_only_degenerate_one(records):
    findings = find_degenerate_composite_disagreements(records)
    assert len(findings) == 1
    f = findings[0]
    assert (f["source_report_year"], f["organism"], f["antibiotic"]) == (
        2019, EC, "nitrofurantoin",
    )
    assert f["shared_tested_n"] == 16741
    assert (f["composite_resistant_n"], f["stratum_resistant_n"]) == (2026, 2042)
    assert f["composite_pct"] == f["stratum_pct"] == 12.0


@needs_pdfs
def test_the_disagreement_is_invisible_to_the_within_cell_check(records):
    """Both nitrofurantoin cells reconcile against their own printed percentage
    -- 2,026/16,741 = 12.10 and 2,042/16,741 = 12.20, both printed as 12. Only a
    cross-column check sees the contradiction."""
    mismatched = {
        (r.organism, r.antibiotic, r.specimen, r.source_report_year)
        for r in internal_consistency(records)
    }
    assert (EC, "nitrofurantoin", ALL_FOUR, 2019) not in mismatched
    assert (EC, "nitrofurantoin", URINE, 2019) not in mismatched


@needs_pdfs
def test_real_composite_sums_are_summarised_but_never_flagged(records):
    rows = summarise_composite_sums(records)
    assert rows, "expected composite columns with a full partition"
    # In the 2019 edition every pooled denominator equals its partition sum
    # exactly, while the numerators do not. That asymmetry is the reason this is
    # reported rather than flagged.
    y2019 = [r for r in rows if r["source_report_year"] == 2019]
    assert y2019
    assert all(r["tested_difference"] == 0 for r in y2019)
    assert any(r["resistant_difference"] != 0 for r in y2019)
    before = {id(r): list(r.flags) for r in records}
    summarise_composite_sums(records)
    assert all(list(r.flags) == before[id(r)] for r in records)


@needs_pdfs
def test_the_pooled_e_coli_column_is_dropped_after_2019(records):
    """The 2019 -> 2020 step moves the specimen axis and not the drug axis,
    which is the case a drug-only comparison would miss entirely."""
    changes = detect_narsnet_panel_changes(narsnet_panel_by_edition(records))
    step = next(
        c for c in changes
        if c["organism"] == EC and (c["from_edition"], c["to_edition"]) == (2019, 2020)
    )
    assert step["specimen_columns_removed"] == [ALL_FOUR]
    assert step["antibiotics_added"] == []
    assert step["antibiotics_removed"] == []


@needs_pdfs
def test_the_2021_edition_moves_both_axes_at_once(records):
    """Eight drugs are added to the E. coli panel and every specimen column is
    replaced: PA+OSBF splits into two columns that are not the same set of
    isolates as it was. No 2021 E. coli column shares a name with a 2020 one, so
    there is no pair to compare edition over edition."""
    changes = detect_narsnet_panel_changes(narsnet_panel_by_edition(records))
    step = next(
        c for c in changes
        if c["organism"] == EC and (c["from_edition"], c["to_edition"]) == (2020, 2021)
    )
    assert set(step["antibiotics_added"]) == {
        "amikacin", "amoxicillin-clavulanate", "cefuroxime", "doxycycline",
        "fosfomycin", "gentamicin", "meropenem", "piperacillin-tazobactam",
    }
    assert step["antibiotics_removed"] == []
    assert step["specimen_columns_added"] == [OSBF, PUS_ASPIRATE]
    assert step["specimen_columns_removed"] == [PA_OSBF]


@needs_pdfs
def test_teicoplanin_is_the_only_s_aureus_panel_addition_in_2021(records):
    changes = detect_narsnet_panel_changes(narsnet_panel_by_edition(records))
    step = next(
        c for c in changes
        if c["organism"] == SA and (c["from_edition"], c["to_edition"]) == (2020, 2021)
    )
    assert step["antibiotics_added"] == ["teicoplanin"]
    assert step["antibiotics_removed"] == []


@needs_pdfs
def test_no_cross_edition_revisions(records):
    assert find_narsnet_cross_report_revisions(records) == []


# --- the corrupt-numerator summary -------------------------------------------


@needs_pdfs
def test_every_declared_block_matches_rows(records):
    """A declaration matching nothing would be dead weight that still reads as a
    live caveat, so it is reported with a zero count rather than dropped."""
    blocks = summarise_corrupt_numerators(records)
    assert blocks
    assert all(b["cells"] > 0 for b in blocks), blocks


@needs_pdfs
def test_the_summary_counts_the_cells_that_do_agree(records):
    """Two of the thirteen Blood cells agree with their own printed percentage.
    Counting them here is what keeps the sub-column-wide declaration honest: the
    number is stated rather than left for a reader to discover."""
    blocks = summarise_corrupt_numerators(records)
    blood = next(b for b in blocks if b["specimen"] == BLOOD)
    assert blood["scope"] == "whole sub-column"
    assert blood["cells"] == 13
    assert blood["cells_agreeing_with_their_printed_pct"] == 2
    assert {a["antibiotic"] for a in blood["agreeing"]} == {
        "amoxicillin-clavulanate", "colistin",
    }

    urine = next(b for b in blocks if b["specimen"] == URINE)
    assert urine["scope"] == ["cotrimoxazole", "piperacillin-tazobactam"]
    assert urine["cells"] == 2
    assert urine["cells_agreeing_with_their_printed_pct"] == 0


@needs_pdfs
def test_the_summary_raises_no_flag_of_its_own(records):
    """The parser has already acted on the declaration. This is a report."""
    before = {id(r): list(r.flags) for r in records}
    summarise_corrupt_numerators(records)
    assert all(list(r.flags) == before[id(r)] for r in records)


@needs_pdfs
def test_corrupt_cells_stay_out_of_the_pct_mismatch_count(records):
    """`pct_mismatch` means a cell's own numerator disagrees with its own
    percentage. Folding fifteen cells with no usable numerator into that count
    would change what the number means."""
    mismatched = internal_consistency(records)
    assert all(r.numerator_status != NUMERATOR_CORRUPT for r in mismatched)
    assert {r.source_report_year for r in mismatched} == {2019, 2020}
    assert len(mismatched) == 8


# --- integration: the committed exports --------------------------------------

CSV_PATH = PROCESSED_DIR / "narsnet_trends.csv"
JSON_PATH = PROCESSED_DIR / "narsnet_trends.json"

needs_export = pytest.mark.skipif(
    not CSV_PATH.exists(), reason="run `python -m src.build_narsnet_dataset` first"
)


@needs_export
def test_export_filename_carries_no_amr_prefix():
    """The filename is the first signal that these are not the same dataset as
    amr_trends.csv and are not concatenable with it."""
    assert CSV_PATH.name == "narsnet_trends.csv"
    assert not CSV_PATH.name.startswith("amr_")
    assert (PROCESSED_DIR / "amr_trends.csv").exists()


@needs_export
def test_export_header_matches_the_schema():
    with open(CSV_PATH, encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    assert header == NARSNET_FIELDNAMES


@needs_export
@needs_pdfs
def test_committed_export_matches_a_fresh_parse(records):
    """Guards against a stale committed export. Everything but `extracted_date`,
    which is the run date, must match what the parser produces today."""
    with open(CSV_PATH, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == len(records)

    fresh = {
        (r.organism, r.antibiotic, r.specimen, r.source_report_year): r
        for r in records
    }
    for row in rows:
        key = (
            row["organism"],
            row["antibiotic"],
            row["specimen"],
            int(row["source_report_year"]),
        )
        rec = fresh[key]
        assert row["tested_n"] == ("" if rec.tested_n is None else str(rec.tested_n))
        assert row["resistant_n"] == (
            "" if rec.resistant_n is None else str(rec.resistant_n)
        )
        assert row["resistant_pct"] == (
            "" if rec.resistant_pct is None else str(rec.resistant_pct)
        )
        assert row["numerator_status"] == rec.numerator_status
        assert row["network"] == "narsnet"


@needs_export
def test_json_and_csv_exports_agree():
    with open(CSV_PATH, encoding="utf-8") as fh:
        csv_rows = list(csv.DictReader(fh))
    with open(JSON_PATH, encoding="utf-8") as fh:
        json_rows = json.load(fh)
    assert len(csv_rows) == len(json_rows)
    for c, j in zip(csv_rows, json_rows):
        assert c["organism"] == j["organism"]
        assert c["antibiotic"] == j["antibiotic"]
        assert c["specimen"] == j["specimen"]


@needs_export
def test_revisions_export_is_empty_and_says_why():
    with open(PROCESSED_DIR / "narsnet_revisions.json", encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["count"] == 0
    assert data["revisions"] == []
    assert "BY DESIGN" in data["note"]


@needs_export
def test_extraction_report_states_the_metric_and_the_scope():
    with open(
        PROCESSED_DIR / "narsnet_extraction_report.json", encoding="utf-8"
    ) as fh:
        data = json.load(fh)
    assert data["network"] == "narsnet"
    assert "PERCENT RESISTANT" in data["metric"]
    assert "never be joined" in data["metric"]
    assert "2019, 2020 and 2021" in data["scope"]
    cross = data["cross_column_checks"]
    assert cross["degenerate_composites"]["count"] == 1
    assert cross["composite_vs_partition_sums"]["count"] > 0
    assert "NO FLAG IS RAISED" in cross["composite_vs_partition_sums"]["description"]


@needs_export
def test_extraction_report_records_the_corrupt_numerators():
    with open(
        PROCESSED_DIR / "narsnet_extraction_report.json", encoding="utf-8"
    ) as fh:
        data = json.load(fh)
    block = data["corrupt_numerators"]
    assert block["cells"] == 15
    assert {b["specimen"] for b in block["blocks"]} == {"blood", "urine"}
    assert all(b["source_report_year"] == 2021 for b in block["blocks"])
    # The two statements the report has to keep apart.
    assert "not that cell" in block["description"]
    assert "nothing is dropped" in block["description"]
    assert (
        "cannot appear here"
        in data["printed_pct_vs_printed_counts"]["description"]
    )


@needs_export
def test_attribution_names_both_networks_and_disclaims_both():
    with open(
        PROCESSED_DIR / "narsnet_extraction_report.json", encoding="utf-8"
    ) as fh:
        attribution = json.load(fh)["attribution"]
    assert "ICMR" in attribution and "NCDC" in attribution
    assert "NARS-Net" in attribution and "AMRSN" in attribution
    assert "not endorsed by or affiliated with ICMR or NCDC" in attribution


# --- integration: a narrow build must not touch the canonical files ----------

CANONICAL = (
    "narsnet_trends.csv",
    "narsnet_trends.json",
    "narsnet_panel.json",
    "narsnet_revisions.json",
    "narsnet_extraction_report.json",
)


def test_coverage_and_completeness_are_derived_from_the_records():
    """Completeness is read off the records, not the CLI arguments, so a parse
    that failed halfway is incomplete for the same reason a filter is."""
    full = [
        make(organism, "ampicillin", BLOOD, year, 10, 5, 50.0)
        for year in (2019, 2020, 2021)
        for organism in (EC, SA)
    ]
    assert builder.coverage(full) == builder.FULL_SCOPE
    assert builder.is_complete(full) is True
    assert builder.is_complete(full[:-1]) is False
    assert builder.is_complete([]) is False


def test_export_refuses_an_incomplete_record_set(tmp_path, monkeypatch, capsys):
    """No PDFs needed: one record is by definition a partial build."""
    monkeypatch.setattr(builder, "PROCESSED_DIR", tmp_path)
    records = [make(EC, "ampicillin", BLOOD, 2019, 10, 5, 50.0)]
    failures, wrote = builder.export(records, [], [], "test")
    assert wrote is False
    assert "[REFUSED]" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []


@needs_pdfs
def test_a_narrow_build_does_not_write_the_canonical_files(tmp_path, monkeypatch):
    """The end-to-end guard. `--year 2019 --organism "Escherichia coli"` parses
    34 of the dataset's 192 rows; before the guard existed it wrote all five
    canonical files with that subset."""
    canonical_before = {
        name: (PROCESSED_DIR / name).read_bytes()
        for name in CANONICAL
        if (PROCESSED_DIR / name).exists()
    }

    monkeypatch.setattr(builder, "PROCESSED_DIR", tmp_path)
    code = builder.main(["--year", "2019", "--organism", "Escherichia coli"])

    assert code == 1, "a build that cannot be exported must not report success"
    assert list(tmp_path.iterdir()) == [], "a narrow build wrote something"

    # And the real files on disk are untouched, byte for byte.
    for name, before in canonical_before.items():
        assert (PROCESSED_DIR / name).read_bytes() == before


@needs_pdfs
def test_a_complete_build_still_writes(tmp_path, monkeypatch, records):
    """The guard must refuse partial builds without refusing every build."""
    monkeypatch.setattr(builder, "PROCESSED_DIR", tmp_path)
    failures, wrote = builder.export(list(records), [], [], "test")
    assert wrote is True
    assert not failures
    for name in CANONICAL:
        assert (tmp_path / name).exists(), name
