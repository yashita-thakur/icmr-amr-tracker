"""Fixture tests (spec section 4.5 / step 3).

Two tiers:

* Pure unit tests of cell parsing and antibiotic normalisation. These need no
  PDFs and always run.
* Integration tests that parse the real 2024 report and assert every fixture in
  `src.validate.FIXTURES`. These skip (rather than fail) when data/raw/ is
  empty, because the PDFs are gitignored per spec section 7 and a fresh clone
  will not have them until `python -m src.fetch` has been run.

Run:  pytest -v
"""

from __future__ import annotations

import pytest

from src.parsers import enterobacterales, nfgnb, staph
from src.parsers.antibiotics import normalise_antibiotic
from src.parsers.base import _join_cell_words, parse_measurement
from src.parsers.trend_parser import parse_report as parse_trend
from src.sources import SOURCES
from src.validate import FIXTURES, check_fixtures, index_records

ALL_SPECS = {}
for _m in (enterobacterales, nfgnb, staph):
    ALL_SPECS.update(_m.SPECS)

# --- unit: cell parsing -----------------------------------------------------


def test_parses_fraction_and_percentage():
    m = parse_measurement("7587 / 12061\n(62.9)")
    assert m.susceptible_n == 7587
    assert m.tested_n == 12061
    assert m.reported_pct == 62.9
    assert m.computed_pct == pytest.approx(62.90, abs=0.01)
    assert m.flags == []


def test_parses_fraction_without_spaces():
    m = parse_measurement("4158/5678 (73.2)")
    assert (m.susceptible_n, m.tested_n, m.reported_pct) == (4158, 5678, 73.2)


def test_flags_low_isolate_count_asterisk():
    m = parse_measurement("*0/8\n(-)")
    assert m.susceptible_n == 0
    assert m.tested_n == 8
    assert m.reported_pct is None
    assert "low_isolate_count_asterisk" in m.flags
    assert "pct_suppressed_in_source" in m.flags


def test_flags_percentage_mismatch():
    # 100/1000 is 10%, but the cell claims 62.9% -- must not pass silently.
    m = parse_measurement("100 / 1000 (62.9)")
    assert any(f.startswith("pct_mismatch") for f in m.flags)


def test_handles_thousands_separator_and_two_dp():
    m = parse_measurement("9,024 / 12,445 (72.51)")
    assert (m.susceptible_n, m.tested_n) == (9024, 12445)


def test_empty_cells():
    for cell in (None, "", "   ", "\n"):
        assert parse_measurement(cell).is_empty


def test_no_isolates_tested_flag():
    m = parse_measurement("*0/0 (-)")
    assert m.tested_n == 0
    assert m.computed_pct is None
    assert "no_isolates_tested" in m.flags


# --- unit: numbers wrapped across a line break inside a cell -----------------


def _word(text, x0, top):
    return {"text": text, "x0": x0, "x1": x0 + 6 * len(text), "top": top,
            "bottom": top + 9}


def test_joins_number_wrapped_across_lines():
    """Narrow cells wrap mid-number: "4286/431" + "1" is 4286/4311, not /431.

    Spacing the two apart yields a denominator short by a digit and a
    susceptibility of 994%.
    """
    joined = _join_cell_words(
        [_word("4286/431", 100, 10), _word("1", 100, 20), _word("(99.4)", 110, 20)]
    )
    assert joined.startswith("4286/4311")
    m = parse_measurement(joined)
    assert (m.susceptible_n, m.tested_n) == (4286, 4311)
    assert not any(f.startswith("pct_mismatch") for f in m.flags)


def test_does_not_splice_a_percentage_onto_a_fraction():
    """A parenthesised percentage on the next line must stay a separate token."""
    joined = _join_cell_words([_word("7587/12061", 100, 10), _word("(62.9)", 100, 20)])
    m = parse_measurement(joined)
    assert (m.susceptible_n, m.tested_n, m.reported_pct) == (7587, 12061, 62.9)


def test_does_not_splice_words_on_the_same_line():
    joined = _join_cell_words(
        [_word("5170", 100, 10), _word("/", 130, 10), _word("14729", 140, 10)]
    )
    assert joined == "5170 / 14729"


# --- unit: antibiotic normalisation -----------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Meropenem", "meropenem"),
        ("meropenem", "meropenem"),
        ("Piperacillin-tazobactam", "piperacillin-tazobactam"),
        ("Piperacillin-\ntazobactam", "piperacillin-tazobactam"),
        ("Piperacillin - Tazobactam", "piperacillin-tazobactam"),
        ("Ciprofloxacin ", "ciprofloxacin"),
        ("Cotrimoxazole", "cotrimoxazole"),
        ("Trimethoprim-sulfamethoxazole", "cotrimoxazole"),
    ],
)
def test_normalise_antibiotic(raw, expected):
    assert normalise_antibiotic(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "AMA", "Year-2024", "N=12445"])
def test_normalise_antibiotic_rejects_non_antibiotics(raw):
    assert normalise_antibiotic(raw) is None


# --- integration: the real 2024 report --------------------------------------

REPORT_YEAR = 2024
_pdf_missing = not SOURCES[REPORT_YEAR].path.exists()
needs_pdf = pytest.mark.skipif(
    _pdf_missing,
    reason="data/raw/{} not present; run `python -m src.fetch` first".format(
        SOURCES[REPORT_YEAR].filename
    ),
)


@pytest.fixture(scope="session")
def records_2024():
    """Every organism, parsed from the 2024 edition."""
    src = SOURCES[REPORT_YEAR]
    recs = []
    for name, spec in ALL_SPECS.items():
        recs.extend(parse_trend(src, spec, extracted_date="test"))
    return recs


@needs_pdf
def test_finds_expected_table_numbers(records_2024):
    """Table numbers printed by the 2024 edition, per chapter."""
    tables = {r.organism: r.source_table for r in records_2024}
    assert tables["Escherichia coli"] == "Table 2.6"
    assert tables["Klebsiella pneumoniae"] == "Table 2.7"
    assert tables["Pseudomonas aeruginosa"] == "Table 3.3"
    assert tables["Acinetobacter baumannii"] == "Table 3.6"
    assert tables["Staphylococcus aureus"] == "Table 6.4"
    assert tables["MRSA"] == "Table 6.9"


@needs_pdf
def test_covers_eight_years(records_2024):
    years = sorted({r.year for r in records_2024})
    assert years == list(range(2017, 2025)), years


@needs_pdf
def test_full_antibiotic_panel(records_2024):
    """Each organism carries its own panel; they are not interchangeable."""
    expected = {
        "Escherichia coli": 10,
        "Klebsiella pneumoniae": 10,
        "Acinetobacter baumannii": 9,
        "Pseudomonas aeruginosa": 11,
        "Staphylococcus aureus": 11,
        "MRSA": 9,
    }
    for organism, count in expected.items():
        abx = {r.antibiotic for r in records_2024 if r.organism == organism}
        assert len(abx) == count, "{}: {}".format(organism, sorted(abx))


@needs_pdf
def test_no_positional_fallback_was_needed(records_2024):
    """Antibiotic labels must be read from the table, never guessed by position."""
    guessed = [
        r for r in records_2024 if "antibiotic_assigned_positionally" in r.flags
    ]
    assert not guessed, "{} record(s) fell back to positional assignment".format(
        len(guessed)
    )


@needs_pdf
def test_spec_fixture_ecoli_meropenem_2024(records_2024):
    """Spec section 4: E. coli / meropenem / 2024 = 62.9%.

    The spec guessed the numerator as 7594; Table 2.6 prints 7587/12061.
    """
    rec = index_records(records_2024)[
        ("Escherichia coli", "meropenem", 2024, 2024)
    ]
    assert rec.susceptible_pct == pytest.approx(62.9, abs=0.05)
    assert rec.susceptible_n == 7587
    assert rec.tested_n == 12061


@needs_pdf
def test_spec_fixture_kpneumoniae_meropenem_2024(records_2024):
    """Spec section 4: K. pneumoniae / meropenem / 2024 = 35.1%."""
    rec = index_records(records_2024)[
        ("Klebsiella pneumoniae", "meropenem", 2024, 2024)
    ]
    assert rec.susceptible_pct == pytest.approx(35.1, abs=0.05)


@needs_pdf
@pytest.mark.parametrize("fx", FIXTURES, ids=lambda f: f.label)
def test_every_fixture(fx, records_2024):
    passes, failures = check_fixtures(records_2024, [fx])
    assert not failures, failures[0]


@needs_pdf
def test_percentages_agree_with_numerator_over_denominator(records_2024):
    """Every printed % must match n/N. A mismatch means mis-paired cells."""
    bad = [r for r in records_2024 if any(f.startswith("pct_mismatch") for f in r.flags)]
    assert not bad, [
        (r.organism, r.antibiotic, r.year, r.flags) for r in bad
    ]


@needs_pdf
def test_no_percentage_is_derived_where_the_source_prints_none(records_2024):
    """The source shows "(-)" instead of a percentage for its tiny cells.

    E. coli / cefazolin / 2017 is 0 susceptible of 8 isolates tested. Deriving
    "0.0%" from that and presenting it as a susceptibility figure would
    introduce a number the source itself does not report, so `susceptible_pct`
    must stay null while the counts are still reported.
    """
    rec = index_records(records_2024)[
        ("Escherichia coli", "cefazolin", 2017, 2024)
    ]
    assert rec.susceptible_n == 0
    assert rec.tested_n == 8
    assert rec.susceptible_pct is None
    assert rec.computed_pct == 0.0  # still available, clearly labelled as derived
    assert "low_isolate_count_asterisk" in rec.flags


@needs_pdf
def test_no_susceptibility_exceeds_one_hundred_percent(records_2024):
    """A susceptibility over 100% means digits were clipped from a cell."""
    bad = [
        r
        for r in records_2024
        if (r.computed_pct is not None and r.computed_pct > 100.0)
        or (r.susceptible_n is not None and r.susceptible_n > (r.tested_n or 0))
    ]
    assert not bad, [
        (r.organism, r.antibiotic, r.year, r.susceptible_n, r.tested_n) for r in bad
    ]


@needs_pdf
def test_denominators_are_never_negative(records_2024):
    bad = [r for r in records_2024 if r.tested_n is not None and r.tested_n < 0]
    assert not bad, [(r.organism, r.antibiotic, r.year, r.tested_n) for r in bad]


@needs_pdf
def test_zero_isolates_tested_is_handled_not_divided_by(records_2024):
    """K. pneumoniae / cefazolin / 2018 is printed "*0/0 (-)" in the source.

    Zero isolates were tested that year, so no percentage exists and none is
    derivable. The row must survive with its counts intact, carry an explicit
    flag, and never produce a division by zero.
    """
    rec = index_records(records_2024)[
        ("Klebsiella pneumoniae", "cefazolin", 2018, 2024)
    ]
    assert rec.tested_n == 0
    assert rec.susceptible_n == 0
    assert rec.susceptible_pct is None
    assert rec.computed_pct is None
    assert "no_isolates_tested" in rec.flags


@needs_pdf
def test_colistin_is_flagged_as_intermediate_for_non_fermenters(records_2024):
    """Both NFGNB tables footnote colistin as INTERMEDIATE susceptibility.

    "*Colistin represents percentage intermediate susceptibility". Read as an
    ordinary susceptibility figure it makes colistin look like the one drug
    still working against A. baumannii at ~97%, so the caveat must travel with
    the data.
    """
    for organism in ("Acinetobacter baumannii", "Pseudomonas aeruginosa"):
        recs = [
            r
            for r in records_2024
            if r.organism == organism and r.antibiotic == "colistin"
        ]
        assert recs, organism
        for r in recs:
            assert "colistin_is_intermediate_susceptibility" in r.flags


@needs_pdf
def test_mrsa_is_cefoxitin_resistant_by_definition(records_2024):
    """MRSA is defined by methicillin/cefoxitin resistance.

    Any non-zero cefoxitin susceptibility in the MRSA table would mean the
    wrong table or the wrong row had been read.
    """
    recs = [
        r for r in records_2024 if r.organism == "MRSA" and r.antibiotic == "cefoxitin"
    ]
    assert len(recs) == 8
    for r in recs:
        assert r.susceptible_pct is None or r.susceptible_pct < 4.0, (r.year, r.susceptible_pct)
