"""V3 NARS-Net extraction tests, 2019 and 2020 editions.

Two tiers, matching `test_known_values.py` and `test_rc_extraction.py`:

* Pure unit tests of the caption grammar, the specimen vocabulary and the
  schema -- no PDFs, always run.
* Integration tests that parse the real NCDC PDFs and assert every cell in
  `HAND_READ` below. These skip (not fail) when `data/raw/` is empty.

Provenance of `HAND_READ`
-------------------------
Every value was read by eye off the rendered PDF page, NOT taken from
`docs/narsnet_v3_research.md`. That document quotes sample rows, and a fixture
copied from it would only prove the parser agrees with the same transcription,
not with the source. Pages read, by PDF page number (the printed page number is
in brackets):

* `narsnet_2019.pdf` p24 [14] -- Table 4, S. aureus, 3 specimen groups x 8 drugs
* `narsnet_2019.pdf` p29 [19] -- Table 6, E. coli, 4 specimen groups x 9 drugs
* `narsnet_2020.pdf` p25 [21] -- Table 5, S. aureus, 3 specimen groups x 8 drugs
* `narsnet_2020.pdf` p33 [29] -- Table 8, E. coli, 3 specimen groups x 9 drugs

108 cells in total, which is every printed cell in the four tables.
"""

from __future__ import annotations

import dataclasses

import pytest

from src.parsers.narsnet_parser import (
    ATOMIC_SPECIMENS,
    CAPTION_RE,
    NARSNET_FIELDNAMES,
    NUMERATOR_NOT_PRINTED,
    NUMERATOR_PRINTED,
    NarsNetRecord,
    SPECS,
    is_composite,
    parse_narsnet_report,
    pct_tolerance,
    specimen_key,
)
from src.sources import NARSNET_SOURCES

EC = "Escherichia coli"
SA = "Staphylococcus aureus"

BLOOD = "blood"
URINE = "urine"
PA_OSBF = "pus_aspirate+osbf"
BLOOD_PA_OSBF = "blood+pus_aspirate+osbf"
ALL_FOUR = "blood+urine+pus_aspirate+osbf"


# --- unit: caption grammar --------------------------------------------------

_REAL_CAPTIONS = [
    ("4", "Table 4 Resistance profile of Staphylococcus aureus"),
    ("6", "Table 6: Resistance profile of E. coli"),
    ("5", "Table 5. Resistance profile of Staphylococcus aureus (N= 9,639)"),
    ("8", "Table 8. Specimen wise resistance profile of E. coli (N=17,271 )"),
]


@pytest.mark.parametrize("expected_table,caption", _REAL_CAPTIONS)
def test_caption_regex_matches_every_printed_wording(expected_table, caption):
    m = CAPTION_RE.search(caption)
    assert m is not None
    assert m.group("table") == expected_table


@pytest.mark.parametrize(
    "caption",
    [
        # The 2020 edition's four-row summary: no counts, no specimen dimension.
        "Table 6 - Overall resistance profile of Staphylococcus aureus isolates "
        "to different antimicrobials",
        # Narrative prose that names a table.
        "(Table 6) Resistance to imipenem is found to be 33% in E. coli blood "
        "isolates",
        # A different table entirely.
        "Table 3 Distribution of Enterobacteriaceae isolates by specimen type",
    ],
)
def test_caption_regex_rejects_non_specimen_tables(caption):
    m = CAPTION_RE.search(caption)
    assert m is None or "overall" in caption.lower()


# --- unit: specimen vocabulary ----------------------------------------------


@pytest.mark.parametrize(
    "header,expected",
    [
        ("Blood (N=4,976)", BLOOD),
        ("Urine (N=18,350)", URINE),
        ("PA+OSBF (N=8,314)", PA_OSBF),
        ("PA + OSBF (N=5,388)", PA_OSBF),
        ("Blood + PA + OSBF (N=13,290)", BLOOD_PA_OSBF),
        ("Blood + PA + OSBF (N=9,639)", BLOOD_PA_OSBF),
        ("Blood + Urine + PA + OSBF (N=24,456)", ALL_FOUR),
    ],
)
def test_specimen_key_reads_every_printed_header(header, expected):
    assert specimen_key(header) == expected


def test_composites_are_distinguishable_from_atomic_strata():
    """A composite must never take an atomic value, or a blood-only filter would
    quietly pick up a pooled column whose denominator is something else."""
    for atomic in ATOMIC_SPECIMENS:
        assert not is_composite(atomic)
    for composite in (PA_OSBF, BLOOD_PA_OSBF, ALL_FOUR):
        assert is_composite(composite)
        assert composite not in ATOMIC_SPECIMENS


def test_composites_name_their_constituents():
    """The 2019 E. coli pooled column includes urine and the 2019 S. aureus one
    does not. One shared 'pooled' name would merge two different denominators."""
    assert ALL_FOUR != BLOOD_PA_OSBF
    assert set(ALL_FOUR.split("+")) - set(BLOOD_PA_OSBF.split("+")) == {URINE}


def test_specimen_order_is_stable_regardless_of_printed_order():
    assert specimen_key("OSBF + PA + Blood") == BLOOD_PA_OSBF


# --- unit: reconciliation tolerance -----------------------------------------


@pytest.mark.parametrize(
    "printed,expected",
    [("87", 0.5), ("12", 0.5), ("0.9", 0.05), ("1.3", 0.05), ("6.3", 0.05)],
)
def test_tolerance_is_half_the_printed_precision(printed, expected):
    assert pct_tolerance(printed) == pytest.approx(expected, abs=1e-6)


# --- unit: schema -----------------------------------------------------------


def test_fieldnames_match_the_dataclass():
    assert NARSNET_FIELDNAMES == [f.name for f in dataclasses.fields(NarsNetRecord)]


def test_schema_carries_no_susceptibility_field():
    """The metric mismatch is structural, not a convention to remember. There is
    no column here that means the same thing as `Record.susceptible_pct`, so the
    two networks cannot be joined on a shared comparison value by accident."""
    names = {f.name for f in dataclasses.fields(NarsNetRecord)}
    assert not [n for n in names if "suscept" in n]
    assert {"resistant_n", "resistant_pct", "numerator_status", "reconcilable"} <= names


def test_schema_has_no_back_computed_numerator_field():
    """A numerator is never derived from denominator x %R: it would be the only
    invented count in the repo, and checking %R against it would be circular."""
    names = {f.name for f in dataclasses.fields(NarsNetRecord)}
    assert not [n for n in names if "implied" in n or "estimated" in n]


# --- integration ------------------------------------------------------------

_missing = [y for y in (2019, 2020) if not NARSNET_SOURCES[y].path.exists()]
needs_pdfs = pytest.mark.skipif(
    _missing,
    reason="data/raw/ missing narsnet {}; run "
    "`python -m src.fetch --network narsnet` first".format(_missing),
)

EXPECTED_TABLES = {
    (SA, 2019): "Table 4",
    (EC, 2019): "Table 6",
    (SA, 2020): "Table 5",
    (EC, 2020): "Table 8",
}

EXPECTED_SPECIMENS = {
    (SA, 2019): {BLOOD_PA_OSBF, BLOOD, PA_OSBF},
    (EC, 2019): {ALL_FOUR, PA_OSBF, BLOOD, URINE},
    (SA, 2020): {BLOOD_PA_OSBF, BLOOD, PA_OSBF},
    (EC, 2020): {PA_OSBF, BLOOD, URINE},
}

EXPECTED_PANELS = {
    (SA, 2019): {"cefoxitin", "gentamicin", "ciprofloxacin", "cotrimoxazole",
                 "clindamycin", "erythromycin", "linezolid", "doxycycline"},
    (SA, 2020): {"cefoxitin", "gentamicin", "ciprofloxacin", "cotrimoxazole",
                 "clindamycin", "erythromycin", "linezolid", "doxycycline"},
    (EC, 2019): {"ampicillin", "cefotaxime", "cefepime", "ertapenem", "imipenem",
                 "ciprofloxacin", "cotrimoxazole", "colistin", "nitrofurantoin"},
    (EC, 2020): {"ampicillin", "cefotaxime", "cefepime", "ertapenem", "imipenem",
                 "ciprofloxacin", "cotrimoxazole", "colistin", "nitrofurantoin"},
}


def _cells(year, organism, specimen, rows):
    return {
        (year, organism, drug, specimen): (tested, resistant, pct)
        for drug, tested, resistant, pct in rows
    }


# Read by eye off the rendered pages named in the module docstring.
HAND_READ: dict = {}
HAND_READ.update(_cells(2019, EC, ALL_FOUR, [
    ("ampicillin", 14943, 12971, 87.0), ("cefotaxime", 18183, 14219, 78.0),
    ("cefepime", 16029, 10531, 66.0), ("ertapenem", 6475, 2545, 39.0),
    ("imipenem", 19124, 6120, 32.0), ("ciprofloxacin", 21162, 16718, 79.0),
    ("cotrimoxazole", 18067, 11563, 64.0), ("colistin", 3205, 16, 0.5),
    ("nitrofurantoin", 16741, 2026, 12.0),
]))
HAND_READ.update(_cells(2019, EC, PA_OSBF, [
    ("ampicillin", 2563, 2327, 91.0), ("cefotaxime", 3310, 2641, 80.0),
    ("cefepime", 3132, 2070, 66.0), ("ertapenem", 1289, 505, 39.0),
    ("imipenem", 3840, 1248, 33.0), ("ciprofloxacin", 3736, 2963, 79.0),
    ("cotrimoxazole", 2613, 1714, 66.0), ("colistin", 540, 7, 1.3),
]))
HAND_READ.update(_cells(2019, EC, BLOOD, [
    ("ampicillin", 1087, 934, 86.0), ("cefotaxime", 1030, 841, 82.0),
    ("cefepime", 1139, 715, 63.0), ("ertapenem", 485, 223, 46.0),
    ("imipenem", 1420, 469, 33.0), ("ciprofloxacin", 1385, 994, 72.0),
    ("cotrimoxazole", 1025, 592, 58.0), ("colistin", 346, 1, 0.3),
]))
HAND_READ.update(_cells(2019, EC, URINE, [
    ("ampicillin", 11293, 9701, 86.0), ("cefotaxime", 13843, 10701, 77.0),
    ("cefepime", 11758, 7748, 66.0), ("ertapenem", 4701, 1805, 38.0),
    ("imipenem", 13864, 4395, 32.0), ("ciprofloxacin", 16041, 12720, 79.0),
    ("cotrimoxazole", 14429, 9249, 64.0), ("colistin", 2319, 7, 0.3),
    ("nitrofurantoin", 16741, 2042, 12.0),
]))
HAND_READ.update(_cells(2019, SA, BLOOD_PA_OSBF, [
    ("cefoxitin", 11855, 6994, 59.0), ("gentamicin", 11342, 2654, 23.0),
    ("ciprofloxacin", 10638, 7042, 66.0), ("cotrimoxazole", 9983, 3813, 38.0),
    ("clindamycin", 12068, 3017, 25.0), ("erythromycin", 12090, 7290, 60.0),
    ("linezolid", 12314, 111, 0.9), ("doxycycline", 8480, 840, 10.0),
]))
HAND_READ.update(_cells(2019, SA, BLOOD, [
    ("cefoxitin", 4499, 2965, 66.0), ("gentamicin", 4390, 1163, 27.0),
    ("ciprofloxacin", 4162, 2322, 56.0), ("cotrimoxazole", 3832, 1747, 46.0),
    ("clindamycin", 4434, 1477, 33.0), ("erythromycin", 4644, 3153, 68.0),
    ("linezolid", 4648, 42, 0.9), ("doxycycline", 3422, 366, 11.0),
]))
HAND_READ.update(_cells(2019, SA, PA_OSBF, [
    ("cefoxitin", 7356, 4031, 55.0), ("gentamicin", 6952, 1495, 22.0),
    ("ciprofloxacin", 6476, 4715, 73.0), ("cotrimoxazole", 6151, 2054, 33.0),
    ("clindamycin", 7634, 1542, 20.0), ("erythromycin", 7446, 4133, 56.0),
    ("linezolid", 7666, 69, 0.9), ("doxycycline", 5058, 470, 9.0),
]))
HAND_READ.update(_cells(2020, SA, BLOOD_PA_OSBF, [
    ("cefoxitin", 8203, 4664, 57.0), ("gentamicin", 8011, 1920, 24.0),
    ("ciprofloxacin", 7110, 4798, 68.0), ("cotrimoxazole", 6872, 2947, 43.0),
    ("clindamycin", 8285, 2232, 27.0), ("erythromycin", 8086, 4675, 58.0),
    ("linezolid", 8083, 79, 1.0), ("doxycycline", 5489, 725, 13.0),
]))
HAND_READ.update(_cells(2020, SA, BLOOD, [
    ("cefoxitin", 3650, 2319, 64.0), ("gentamicin", 3572, 929, 26.0),
    ("ciprofloxacin", 3047, 1898, 62.0), ("cotrimoxazole", 2866, 1467, 51.0),
    ("clindamycin", 3629, 1221, 34.0), ("erythromycin", 3629, 2451, 68.0),
    ("linezolid", 3519, 26, 1.0), ("doxycycline", 2638, 24, 12.0),
]))
HAND_READ.update(_cells(2020, SA, PA_OSBF, [
    ("cefoxitin", 4580, 2357, 52.0), ("gentamicin", 4467, 1001, 22.0),
    ("ciprofloxacin", 4087, 2922, 72.0), ("cotrimoxazole", 4032, 1493, 37.0),
    ("clindamycin", 4684, 1019, 22.0), ("erythromycin", 4487, 2244, 50.0),
    ("linezolid", 4592, 43, 1.0), ("doxycycline", 2867, 402, 14.0),
]))
HAND_READ.update(_cells(2020, EC, PA_OSBF, [
    ("ampicillin", 2590, 2291, 89.0), ("cefotaxime", 2946, 2340, 79.0),
    ("cefepime", 2332, 1468, 63.0), ("ertapenem", 900, 275, 31.0),
    ("imipenem", 3400, 801, 24.0), ("ciprofloxacin", 3063, 2156, 70.0),
    ("cotrimoxazole", 2522, 1613, 64.0), ("colistin", 454, 7, 1.5),
    # Denominator printed, numerator and percentage greyed out.
    ("nitrofurantoin", 154, None, None),
]))
HAND_READ.update(_cells(2020, EC, BLOOD, [
    ("ampicillin", 800, 688, 86.0), ("cefotaxime", 821, 654, 80.0),
    ("cefepime", 856, 573, 67.0), ("ertapenem", 272, 109, 40.0),
    ("imipenem", 1049, 330, 32.0), ("ciprofloxacin", 948, 600, 63.0),
    ("cotrimoxazole", 852, 505, 59.0), ("colistin", 345, 2, 0.6),
]))
HAND_READ.update(_cells(2020, EC, URINE, [
    ("ampicillin", 7188, 6279, 87.0), ("cefotaxime", 8068, 6169, 77.0),
    ("cefepime", 6097, 3807, 62.0), ("ertapenem", 1980, 528, 27.0),
    ("imipenem", 8412, 1815, 22.0), ("ciprofloxacin", 8796, 6156, 70.0),
    ("cotrimoxazole", 8197, 5136, 63.0), ("nitrofurantoin", 9376, 1113, 12.0),
    ("colistin", 493, 31, 6.3),
]))

# Cells where the printed percentage does not follow from the printed counts,
# read off the same pages. Seven sit just past the half-point of the printed
# precision, which is the source rounding a percentage it did not compute from
# the counts it printed. The eighth is a different animal: 24 resistant of 2,638
# is 0.9%, not the 12% printed beside it.
EXPECTED_MISMATCHES = {
    (2019, SA, "gentamicin", BLOOD),
    (2020, SA, "cefoxitin", PA_OSBF),
    (2020, SA, "ciprofloxacin", BLOOD_PA_OSBF),
    (2020, SA, "ciprofloxacin", PA_OSBF),
    (2020, SA, "doxycycline", BLOOD),
    (2020, EC, "ampicillin", PA_OSBF),
    (2020, EC, "cefotaxime", URINE),
    (2020, EC, "imipenem", BLOOD),
}


@pytest.fixture(scope="session")
def narsnet_records():
    recs = []
    for (organism, year) in EXPECTED_TABLES:
        recs.extend(
            parse_narsnet_report(
                NARSNET_SOURCES[year], SPECS[organism], extracted_date="test"
            )
        )
    return recs


def _index(records):
    return {
        (r.source_report_year, r.organism, r.antibiotic, r.specimen): r
        for r in records
    }


@needs_pdfs
def test_table_numbers_are_read_from_each_edition(narsnet_records):
    seen = {
        (r.organism, r.source_report_year): r.source_table for r in narsnet_records
    }
    assert seen == EXPECTED_TABLES


@needs_pdfs
def test_the_2020_overall_summary_table_is_not_picked_up(narsnet_records):
    """The 2020 edition prints Table 5 (specimen-wise, with counts) and Table 6
    (four rows, %R only). Landing on Table 6 would lose the specimen dimension
    and every denominator."""
    tables = {
        r.source_table for r in narsnet_records
        if r.organism == SA and r.source_report_year == 2020
    }
    assert tables == {"Table 5"}


@needs_pdfs
@pytest.mark.parametrize("key,expected", sorted(EXPECTED_SPECIMENS.items(), key=str))
def test_specimen_columns_per_table(key, expected, narsnet_records):
    organism, year = key
    seen = {
        r.specimen for r in narsnet_records
        if r.organism == organism and r.source_report_year == year
    }
    assert seen == expected


@needs_pdfs
@pytest.mark.parametrize("key,expected", sorted(EXPECTED_PANELS.items(), key=str))
def test_drug_panel_per_table(key, expected, narsnet_records):
    organism, year = key
    seen = {
        r.antibiotic for r in narsnet_records
        if r.organism == organism and r.source_report_year == year
    }
    assert seen == expected


@needs_pdfs
def test_every_hand_read_cell_matches(narsnet_records):
    index = _index(narsnet_records)
    wrong = []
    for key, (tested, resistant, pct) in sorted(HAND_READ.items(), key=str):
        rec = index.get(key)
        if rec is None:
            wrong.append("{}: no record extracted".format(key))
            continue
        got = (rec.tested_n, rec.resistant_n, rec.resistant_pct)
        if got != (tested, resistant, pct):
            wrong.append("{}: hand-read {}, parsed {}".format(key, (tested, resistant, pct), got))
    assert not wrong, "\n".join(wrong)


@needs_pdfs
def test_no_cell_is_extracted_that_was_not_hand_read(narsnet_records):
    """The reverse direction: a phantom row invented by the grid would show up
    here even though every hand-read cell still matched."""
    assert set(_index(narsnet_records)) == set(HAND_READ)


@needs_pdfs
@pytest.mark.parametrize(
    "key",
    [
        (2019, EC, "cefotaxime", BLOOD),
        (2019, EC, "colistin", URINE),
        (2019, SA, "linezolid", BLOOD_PA_OSBF),
        (2020, EC, "ertapenem", BLOOD),
        (2020, SA, "doxycycline", PA_OSBF),
    ],
)
def test_spot_cells(key, narsnet_records):
    rec = _index(narsnet_records)[key]
    assert (rec.tested_n, rec.resistant_n, rec.resistant_pct) == HAND_READ[key]
    assert rec.numerator_status == NUMERATOR_PRINTED
    assert rec.reconcilable is True


@needs_pdfs
def test_printed_numerators_are_flagged_where_they_do_not_reconcile(narsnet_records):
    seen = {
        (r.source_report_year, r.organism, r.antibiotic, r.specimen)
        for r in narsnet_records
        if any(f.startswith("pct_mismatch") for f in r.flags)
    }
    assert seen == EXPECTED_MISMATCHES


@needs_pdfs
def test_the_2020_doxycycline_blood_cell_is_the_gross_one(narsnet_records):
    """2,638 tested, 24 resistant, printed 12%. Flagged and kept as printed --
    the numerator is not corrected and the percentage is not recomputed."""
    rec = _index(narsnet_records)[(2020, SA, "doxycycline", BLOOD)]
    assert (rec.tested_n, rec.resistant_n, rec.resistant_pct) == (2638, 24, 12.0)
    assert rec.computed_pct == pytest.approx(0.91, abs=0.01)
    assert any(f.startswith("pct_mismatch") for f in rec.flags)


@needs_pdfs
def test_a_greyed_out_numerator_is_not_mistaken_for_zero(narsnet_records):
    """2020 E. coli, nitrofurantoin, PA+OSBF: the denominator is printed and the
    numerator and percentage are greyed out. Absent is not zero."""
    rec = _index(narsnet_records)[(2020, EC, "nitrofurantoin", PA_OSBF)]
    assert rec.tested_n == 154
    assert rec.resistant_n is None
    assert rec.resistant_pct is None
    assert rec.numerator_status == NUMERATOR_NOT_PRINTED
    assert rec.reconcilable is False
    assert rec.computed_pct is None
    assert "numerator_not_printed_in_source" in rec.flags
    assert "pct_suppressed_in_source" in rec.flags


@needs_pdfs
def test_fully_greyed_blocks_emit_no_row(narsnet_records):
    """2019 E. coli nitrofurantoin is printed for the pooled and urine columns
    only; the blood and PA+OSBF blocks are greyed out entirely. Nothing was
    printed there, so nothing is emitted."""
    seen = {
        r.specimen for r in narsnet_records
        if r.organism == EC and r.source_report_year == 2019
        and r.antibiotic == "nitrofurantoin"
    }
    assert seen == {ALL_FOUR, URINE}


@needs_pdfs
def test_provenance_is_carried_on_every_row(narsnet_records):
    for r in narsnet_records:
        assert r.network == "narsnet"
        assert r.year == r.source_report_year
        assert r.source_url.startswith("https://ncdc.mohfw.gov.in/uploads/pdf/")
        assert r.source_table.startswith("Table ")
        # 2019 and 2020 are exactly the two editions whose cover year is not
        # their reporting period.
        assert r.source_cover_year == {2019: 2020, 2020: 2021}[r.source_report_year]


@needs_pdfs
def test_no_confidence_intervals_before_2022(narsnet_records):
    """The 95% CI column arrives in the 2022 edition. Nothing here should invent
    one."""
    assert all(r.ci_low is None and r.ci_high is None for r in narsnet_records)


@needs_pdfs
def test_reconcilable_tracks_the_printed_numerator(narsnet_records):
    for r in narsnet_records:
        if r.numerator_status == NUMERATOR_PRINTED:
            assert r.reconcilable is True
            assert r.computed_pct is not None
        else:
            assert r.reconcilable is False
            assert r.computed_pct is None
