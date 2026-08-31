"""V2 Regional Centre extraction tests.

Two tiers, matching `test_known_values.py`:

* Pure unit tests of the RC caption grammar -- no PDFs, always run.
* Integration tests that parse the real report PDFs and assert every fixture in
  `src.rc_validate.RC_FIXTURES`, the RC panel each edition prints, and the
  panel-changed flagging. These skip (not fail) when data/raw/ is empty.
"""

from __future__ import annotations

import re

import pytest

from src.parsers.rc_parser import (
    RC_CAPTION_RE,
    SPECS,
    parse_rc_report,
)
from src.rc_validate import (
    RC_FIXTURES,
    apply_rc_panel_flags,
    check_rc_fixtures,
    detect_rc_panel_changes,
    find_rc_cross_report_revisions,
    index_rc_records,
)
from src.sources import SOURCES

# --- unit: caption grammar -------------------------------------------------

# Every RC-wise AMS caption actually printed, across all three editions and the
# two grammatical orderings ("... Percentage RC wise of X ..." in 2022/2023,
# "RC-wise ... percentages of X ..." in 2024).
_REAL_CAPTIONS = [
    ("Table 3.10", "Table 3.10: Antimicrobial Susceptibilities (AMS) Percentage "
     "RC wise of Escherichia coli from Total (Except Faeces & Urine)"),
    ("Table 3.11", "Table 3.11: Antimicrobial Susceptibilities (AMS) Percentage "
     "RC wise of K. pneumoniae from total (Except faeces & urine)"),
    ("Table 7.3", "Table 7.3: Antimicrobial Susceptibility (AMS) Percentage RC "
     "wise of Staphylococcus aureus from all samples except faeces and urine"),
    ("Table 2.10", "Table 2.10: RC-wise Antimicrobial Susceptibility (AMS) "
     "percentages of Escherichia coli from total samples (except faeces & urine)"),
    ("Table 2.11", "Table 2.11: RC-wise AMS percentages of K. pneumoniae from "
     "total samples (except faeces & urine)"),
    ("Table 6.3", "Table 6.3: RC-wise AMS percentages of S. aureus from all "
     "samples (except faeces and urine)"),
]


@pytest.mark.parametrize("expected_table,caption", _REAL_CAPTIONS)
def test_rc_caption_regex_matches_every_printed_wording(expected_table, caption):
    m = RC_CAPTION_RE.search(caption)
    assert m is not None
    assert "Table " + m.group("table") == expected_table


@pytest.mark.parametrize(
    "caption",
    [
        # National yearly-trend caption: no "RC wise", no "AMS".
        "Table 2.6: Yearly susceptibility trend of E. coli isolated from all "
        "samples (except faeces and urine)",
        # Isolate-count distribution, not susceptibility: no "AMS".
        "Table 1.6: Regional centre wise distribution of major species of "
        "family Enterobacterales",
        # 2022 urine-only RC breakdown: no "AMS".
        "Table 3.13: Susceptibility of E. coli isolated from urine, overall and "
        "RC wise",
    ],
)
def test_rc_caption_regex_rejects_non_rc_ams_tables(caption):
    assert RC_CAPTION_RE.search(caption) is None


def test_rc_caption_regex_needs_both_rc_wise_and_ams():
    assert RC_CAPTION_RE.search("Table 9.9: RC-wise AMS percentages of X from all")
    assert not RC_CAPTION_RE.search("Table 9.9: RC-wise percentages of X from all")
    assert not RC_CAPTION_RE.search("Table 9.9: AMS percentages of X from all")


# --- integration: the real report PDFs -----------------------------------

_missing = [y for y in (2022, 2023, 2024) if not SOURCES[y].path.exists()]
needs_pdfs = pytest.mark.skipif(
    _missing,
    reason="data/raw/ missing {}; run `python -m src.fetch` first".format(_missing),
)

# (organism, edition) -> the table number that edition printed.
EXPECTED_TABLES = {
    ("Escherichia coli", 2023): "Table 3.10",
    ("Escherichia coli", 2024): "Table 2.10",
    ("Klebsiella pneumoniae", 2023): "Table 3.11",
    ("Klebsiella pneumoniae", 2024): "Table 2.11",
    ("Staphylococcus aureus", 2022): "Table 6.3",
    ("Staphylococcus aureus", 2023): "Table 7.3",
    ("Staphylococcus aureus", 2024): "Table 6.3",
}

ENTERO_RC_PANEL = {
    "piperacillin-tazobactam", "cefotaxime", "ceftazidime", "ertapenem",
    "imipenem", "meropenem", "amikacin", "ciprofloxacin", "levofloxacin",
}
SAUREUS_RC_PANEL = {
    "cefoxitin", "oxacillin", "vancomycin", "teicoplanin", "erythromycin",
    "tetracycline", "tigecycline", "ciprofloxacin", "clindamycin",
    "cotrimoxazole", "linezolid",
}

# RC row set each edition prints for each organism (verified by hand against the
# printed tables). RC codes are anonymised and edition-scoped.
EXPECTED_RC_SETS = {
    ("Escherichia coli", 2023): {f"RC{i}" for i in range(1, 22)},
    ("Escherichia coli", 2024): {f"RC{i}" for i in range(1, 22)} - {"RC15"},
    ("Klebsiella pneumoniae", 2023): {f"RC{i}" for i in range(1, 22)},
    ("Klebsiella pneumoniae", 2024): {f"RC{i}" for i in range(1, 22)} - {"RC15"},
    ("Staphylococcus aureus", 2022): {f"RC{i}" for i in range(1, 22)},
    ("Staphylococcus aureus", 2023): {f"RC{i}" for i in range(1, 22)} - {"RC18"},
    ("Staphylococcus aureus", 2024): {f"RC{i}" for i in range(1, 22)}
    - {"RC1", "RC15", "RC18"},
}


@pytest.fixture(scope="session")
def rc_records():
    recs = []
    for (organism, year), _tbl in EXPECTED_TABLES.items():
        recs.extend(
            parse_rc_report(SOURCES[year], SPECS[organism], extracted_date="test")
        )
    apply_rc_panel_flags(recs)
    return recs


@needs_pdfs
def test_table_numbers_are_read_from_each_edition(rc_records):
    seen = {
        (r.organism, r.source_report_year): r.source_table for r in rc_records
    }
    assert seen == EXPECTED_TABLES


@needs_pdfs
def test_2022_edition_has_no_ecoli_or_kpneumoniae_rc_table():
    """The 2022 edition breaks these down by RC for urine only (out of scope)."""
    for organism in ("Escherichia coli", "Klebsiella pneumoniae"):
        with pytest.raises(LookupError):
            parse_rc_report(SOURCES[2022], SPECS[organism], extracted_date="test")


@needs_pdfs
@pytest.mark.parametrize("key,expected", sorted(EXPECTED_RC_SETS.items()))
def test_rc_panel_each_edition_prints(rc_records, key, expected):
    organism, year = key
    got = {
        r.regional_centre
        for r in rc_records
        if r.organism == organism and r.source_report_year == year
    }
    assert got == expected


@needs_pdfs
def test_antibiotic_panels_are_read_from_the_table(rc_records):
    for organism, panel in (
        ("Escherichia coli", ENTERO_RC_PANEL),
        ("Klebsiella pneumoniae", ENTERO_RC_PANEL),
        ("Staphylococcus aureus", SAUREUS_RC_PANEL),
    ):
        got = {r.antibiotic for r in rc_records if r.organism == organism}
        assert got == panel, (organism, got ^ panel)


@needs_pdfs
def test_every_row_year_equals_its_edition(rc_records):
    """RC-wise tables are single-year cross-sections: no retrospective axis."""
    assert all(r.year == r.source_report_year for r in rc_records)


@needs_pdfs
def test_no_susceptibility_exceeds_one_hundred(rc_records):
    bad = [
        (r.organism, r.regional_centre, r.antibiotic, r.susceptible_n, r.tested_n)
        for r in rc_records
        if (r.computed_pct is not None and r.computed_pct > 100.0)
        or (r.susceptible_n is not None and r.susceptible_n > (r.tested_n or 0))
    ]
    assert not bad


@needs_pdfs
@pytest.mark.parametrize("fx", RC_FIXTURES, ids=lambda f: f.label)
def test_every_rc_fixture(fx, rc_records):
    _passes, failures = check_rc_fixtures(rc_records, [fx])
    assert not failures, failures[0]


@needs_pdfs
def test_panel_changed_flag_is_on_the_later_editions_only(rc_records):
    changes = {
        (c["organism"], c["edition"]): c for c in detect_rc_panel_changes(rc_records)
    }
    # E. coli / K. pneumoniae: 2024 drops RC15 vs the 2023 baseline.
    for organism in ("Escherichia coli", "Klebsiella pneumoniae"):
        assert (organism, 2024) in changes
        assert changes[(organism, 2024)]["dropped"] == ["RC15"]
        assert changes[(organism, 2024)]["baseline_edition"] == 2023
    # S. aureus: baseline is 2022; 2023 drops RC18, 2024 drops RC1/RC15/RC18.
    assert changes[("Staphylococcus aureus", 2023)]["dropped"] == ["RC18"]
    assert changes[("Staphylococcus aureus", 2024)]["dropped"] == [
        "RC1", "RC15", "RC18"
    ]

    for r in rc_records:
        flagged = any(f.startswith("rc_panel_changed(") for f in r.flags)
        in_changed_edition = (r.organism, r.source_report_year) in changes
        assert flagged == in_changed_edition


@needs_pdfs
def test_cross_edition_revisions_are_empty_by_construction(rc_records):
    """Single-year cross-sections: no (organism, RC, antibiotic, year) key is
    covered by two editions, so there is nothing to revise. This asserts the
    'near-empty by design' claim in the README rather than leaving it implicit.
    """
    assert find_rc_cross_report_revisions(rc_records) == []


@needs_pdfs
def test_low_count_cells_that_dont_reconcile_are_flagged_not_adjusted(rc_records):
    """In the 2023 edition, three tiny-denominator RC cells (1/16, 2/3, 1/1)
    print a percentage of 0 where their own counts would round differently.
    Carried as printed and flagged pct_mismatch, not adjusted -- same policy
    as V1.
    """
    idx = index_rc_records(rc_records)
    for organism, rc, drug, n, d in [
        ("Klebsiella pneumoniae", "RC7", "levofloxacin", 1, 16),
        ("Staphylococcus aureus", "RC2", "tigecycline", 2, 3),
        ("Staphylococcus aureus", "RC3", "teicoplanin", 1, 1),
    ]:
        r = idx[(organism, rc, drug, 2023)]
        assert (r.susceptible_n, r.tested_n) == (n, d)
        assert r.susceptible_pct == 0.0
        assert any(f.startswith("pct_mismatch") for f in r.flags)


@needs_pdfs
def test_grid_reconciles_apart_from_the_three_flagged_cells(rc_records):
    bad = [
        (r.organism, r.source_report_year, r.regional_centre, r.antibiotic)
        for r in rc_records
        if any(f.startswith("pct_mismatch") for f in r.flags)
    ]
    assert len(bad) == 3, bad
