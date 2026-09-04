"""V3 NARS-Net extraction tests, the 2019 to 2024 editions.

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
* `narsnet_2021.pdf` p24 [15] -- Table 4, S. aureus, 3 specimen groups x 9 drugs
* `narsnet_2021.pdf` p29 [20] -- Table 6, E. coli, 4 specimen groups x 17 drugs
* `narsnet_2022.pdf` p36 [20] -- Table 5, S. aureus, 3 specimen groups x 9 drugs
* `narsnet_2022.pdf` p44 [28] -- Table 7, E. coli, 4 specimen groups x 17 drugs
* `narsnet_2023.pdf` p30 [20] -- Table 6, S. aureus, 3 specimen groups x 9 drugs
* `narsnet_2023.pdf` p38 [28] -- Table 8, E. coli, 4 specimen groups x 17 drugs
* `narsnet_2024.pdf` p25 [18] -- Table 6, S. aureus, 3 specimen groups x 9 drugs
* `narsnet_2024.pdf` p34 [unnumbered; p33 is 26 and p35 is 28]
                            -- Table 8, E. coli, 4 specimen groups x 17 drugs

450 cells in total, which is every printed cell in the twelve tables.

The 2021 figures, and then the 2022-2024 figures, were each read the same way
and in the same order as the rest, before being compared against what
`docs/narsnet_v3_research.md` says about those editions, so the reading is
evidence for that document rather than a copy of it.

Two dictionaries, because the editions do not print the same columns.
`HAND_READ` holds the 2019-2021 cells as (Number Tested, Number Resistant, %R).
`HAND_READ_CI` holds the 2022-2024 cells as (Number Tested, %R, CI low, CI
high): those editions print no numerator at all and a 95% confidence interval in
its place.
"""

from __future__ import annotations

import dataclasses

import pytest

from src.parsers.narsnet_parser import (
    ATOMIC_SPECIMENS,
    CAPTION_RE,
    CORRUPT_NUMERATORS,
    NARSNET_FIELDNAMES,
    NUMERATOR_CORRUPT,
    NUMERATOR_NOT_PRINTED,
    NUMERATOR_PRINTED,
    NarsNetRecord,
    SPECS,
    find_corrupt_numerators,
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
PUS_ASPIRATE = "pus_aspirate"
OSBF = "osbf"
PA_OSBF = "pus_aspirate+osbf"
BLOOD_PA_OSBF = "blood+pus_aspirate+osbf"
ALL_FOUR = "blood+urine+pus_aspirate+osbf"


# --- unit: caption grammar --------------------------------------------------

_REAL_CAPTIONS = [
    ("4", "Table 4 Resistance profile of Staphylococcus aureus"),
    ("6", "Table 6: Resistance profile of E. coli"),
    ("5", "Table 5. Resistance profile of Staphylococcus aureus (N= 9,639)"),
    ("8", "Table 8. Specimen wise resistance profile of E. coli (N=17,271 )"),
    # The 2021 edition uses two wordings in the same document.
    ("4", "Table 4: Resistance profile observed in Staphylococcus aureus"),
    ("6", "Table 6: Resistance profile of Escherichia coli"),
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
        # The 2021 edition spells the same two strata out.
        ("Pus aspirate (N=7946)", PUS_ASPIRATE),
        ("Pus Aspirate (N=6434)", PUS_ASPIRATE),
        ("Other Sterile Body Fluids (N=630)", OSBF),
        ("OSBF (N=675)", OSBF),
    ],
)
def test_specimen_key_reads_every_printed_header(header, expected):
    assert specimen_key(header) == expected


def test_a_spelled_out_heading_is_one_specimen_not_four():
    """"Other Sterile Body Fluids" is matched as a phrase before the word-by-word
    pass, so its four words cannot be read as four separate strata."""
    assert specimen_key("Other Sterile Body Fluids (N=630)") == OSBF
    assert "+" not in specimen_key("Pus Aspirate (N=6434)")


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

_missing = [
    y for y in (2019, 2020, 2021, 2022, 2023, 2024)
    if not NARSNET_SOURCES[y].path.exists()
]
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
    (SA, 2021): "Table 4",
    (EC, 2021): "Table 6",
    (SA, 2022): "Table 5",
    (EC, 2022): "Table 7",
    (SA, 2023): "Table 6",
    (EC, 2023): "Table 8",
    (SA, 2024): "Table 6",
    (EC, 2024): "Table 8",
}

# The editions that print a numerator, and the editions that print a 95% CI
# instead. No edition prints both.
COUNT_YEARS = (2019, 2020, 2021)
CI_YEARS = (2022, 2023, 2024)

EXPECTED_SPECIMENS = {
    (SA, 2019): {BLOOD_PA_OSBF, BLOOD, PA_OSBF},
    (EC, 2019): {ALL_FOUR, PA_OSBF, BLOOD, URINE},
    (SA, 2020): {BLOOD_PA_OSBF, BLOOD, PA_OSBF},
    (EC, 2020): {PA_OSBF, BLOOD, URINE},
    # 2021 reports pus aspirate and OSBF as separate columns and prints no
    # pooled column at all.
    (SA, 2021): {BLOOD, PUS_ASPIRATE, OSBF},
    (EC, 2021): {BLOOD, PUS_ASPIRATE, OSBF, URINE},
    (SA, 2022): {BLOOD, PUS_ASPIRATE, OSBF},
    (EC, 2022): {BLOOD, PUS_ASPIRATE, OSBF, URINE},
    (SA, 2023): {BLOOD, PUS_ASPIRATE, OSBF},
    (EC, 2023): {BLOOD, PUS_ASPIRATE, OSBF, URINE},
    (SA, 2024): {BLOOD, PUS_ASPIRATE, OSBF},
    (EC, 2024): {BLOOD, PUS_ASPIRATE, OSBF, URINE},
}

_SA_2021_PANEL = {
    "cefoxitin", "gentamicin", "ciprofloxacin", "cotrimoxazole", "clindamycin",
    "erythromycin", "linezolid", "doxycycline", "teicoplanin",
}
# 2021 and 2022 print the same seventeen E. coli molecules.
_EC_2021_PANEL = {
    "ampicillin", "cefotaxime", "cefepime", "ertapenem", "imipenem",
    "ciprofloxacin", "cotrimoxazole", "colistin", "nitrofurantoin", "amikacin",
    "amoxicillin-clavulanate", "gentamicin", "meropenem",
    "piperacillin-tazobactam", "fosfomycin", "cefuroxime", "doxycycline",
}
# 2023 drops cefuroxime and adds ceftriaxone, and the panel is seventeen drugs
# either side of the change.
_EC_2023_PANEL = (_EC_2021_PANEL - {"cefuroxime"}) | {"ceftriaxone"}

EXPECTED_PANELS = {
    (SA, 2019): {"cefoxitin", "gentamicin", "ciprofloxacin", "cotrimoxazole",
                 "clindamycin", "erythromycin", "linezolid", "doxycycline"},
    (SA, 2020): {"cefoxitin", "gentamicin", "ciprofloxacin", "cotrimoxazole",
                 "clindamycin", "erythromycin", "linezolid", "doxycycline"},
    (SA, 2021): _SA_2021_PANEL,
    (EC, 2019): {"ampicillin", "cefotaxime", "cefepime", "ertapenem", "imipenem",
                 "ciprofloxacin", "cotrimoxazole", "colistin", "nitrofurantoin"},
    (EC, 2020): {"ampicillin", "cefotaxime", "cefepime", "ertapenem", "imipenem",
                 "ciprofloxacin", "cotrimoxazole", "colistin", "nitrofurantoin"},
    (EC, 2021): _EC_2021_PANEL,
    (SA, 2022): _SA_2021_PANEL,
    (EC, 2022): _EC_2021_PANEL,
    (SA, 2023): _SA_2021_PANEL,
    (EC, 2023): _EC_2023_PANEL,
    (SA, 2024): _SA_2021_PANEL,
    (EC, 2024): _EC_2023_PANEL,
}


def _cells(year, organism, specimen, rows):
    return {
        (year, organism, drug, specimen): (tested, resistant, pct)
        for drug, tested, resistant, pct in rows
    }


def _ci_cells(year, organism, specimen, rows):
    return {
        (year, organism, drug, specimen): (tested, pct, low, high)
        for drug, tested, pct, low, high in rows
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

# --- 2021, p24 [15] and p29 [20] --------------------------------------------
# Read the same way as the four tables above. Every figure below is what the
# page prints, including the fifteen E. coli cells whose printed numerator is
# not that cell's numerator: this file records what was printed, and
# `CORRUPT_NUMERATORS` records which of it can be used.
HAND_READ.update(_cells(2021, SA, BLOOD, [
    ("cefoxitin", 5805, 3441, 59.0), ("ciprofloxacin", 5357, 2695, 50.0),
    ("clindamycin", 5755, 1960, 34.0), ("doxycycline", 5419, 863, 16.0),
    ("erythromycin", 5911, 3730, 63.0), ("gentamicin", 5437, 1396, 26.0),
    ("linezolid", 5761, 36, 1.0), ("cotrimoxazole", 4656, 2015, 43.0),
    ("teicoplanin", 1206, 14, 1.0),
]))
HAND_READ.update(_cells(2021, SA, PUS_ASPIRATE, [
    ("cefoxitin", 7602, 3703, 49.0), ("ciprofloxacin", 6607, 3884, 59.0),
    ("clindamycin", 7295, 1630, 22.0), ("doxycycline", 6215, 796, 13.0),
    ("erythromycin", 7430, 3807, 51.0), ("gentamicin", 7258, 1698, 23.0),
    ("linezolid", 7452, 49, 1.0), ("cotrimoxazole", 6680, 1803, 27.0),
    ("teicoplanin", 1662, 30, 2.0),
]))
HAND_READ.update(_cells(2021, SA, OSBF, [
    ("cefoxitin", 608, 294, 48.0), ("ciprofloxacin", 524, 209, 40.0),
    ("clindamycin", 588, 160, 27.0), ("doxycycline", 533, 50, 9.0),
    ("erythromycin", 626, 341, 54.0), ("gentamicin", 584, 121, 21.0),
    ("linezolid", 629, 9, 1.0), ("cotrimoxazole", 514, 191, 37.0),
    ("teicoplanin", 96, 1, 1.0),
]))
HAND_READ.update(_cells(2021, EC, BLOOD, [
    ("amikacin", 1510, 1088, 29.0), ("amoxicillin-clavulanate", 680, 390, 57.0),
    ("ampicillin", 1294, 584, 84.0), ("cefepime", 1286, 1056, 62.0),
    ("cefotaxime", 1380, 797, 77.0), ("ciprofloxacin", 1551, 135, 63.0),
    ("colistin", 914, 0, 0.0), ("ertapenem", 406, 211, 33.0),
    ("gentamicin", 1260, 431, 39.0), ("imipenem", 1593, 491, 29.0),
    # 981 resistant of 854 tested, as printed.
    ("meropenem", 854, 981, 25.0),
    ("piperacillin-tazobactam", 1350, 701, 43.0),
    ("cotrimoxazole", 1289, 14, 54.0),
]))
HAND_READ.update(_cells(2021, EC, PUS_ASPIRATE, [
    ("amikacin", 5399, 1280, 24.0), ("amoxicillin-clavulanate", 2848, 1660, 58.0),
    ("ampicillin", 4986, 4281, 86.0), ("cefepime", 4999, 3014, 60.0),
    ("cefotaxime", 5302, 4045, 76.0), ("ciprofloxacin", 5820, 4266, 73.0),
    ("colistin", 1847, 0, 0.0), ("ertapenem", 1186, 283, 24.0),
    ("gentamicin", 4775, 1696, 36.0), ("imipenem", 5810, 1193, 21.0),
    ("meropenem", 3605, 592, 16.0),
    ("piperacillin-tazobactam", 5293, 2268, 43.0),
    ("cotrimoxazole", 4971, 2872, 58.0), ("doxycycline", 762, 398, 52.0),
]))
HAND_READ.update(_cells(2021, EC, OSBF, [
    ("amikacin", 565, 121, 21.0), ("amoxicillin-clavulanate", 262, 151, 58.0),
    ("ampicillin", 501, 417, 83.0), ("cefepime", 548, 327, 60.0),
    ("cefotaxime", 577, 447, 77.0), ("ciprofloxacin", 644, 454, 70.0),
    ("colistin", 337, 0, 0.0), ("ertapenem", 186, 46, 25.0),
    ("gentamicin", 421, 132, 31.0), ("imipenem", 646, 161, 25.0),
    ("meropenem", 302, 58, 19.0), ("piperacillin-tazobactam", 547, 257, 47.0),
    ("cotrimoxazole", 516, 308, 60.0), ("doxycycline", 111, 49, 44.0),
]))
HAND_READ.update(_cells(2021, EC, URINE, [
    ("amikacin", 12006, 2323, 19.0), ("amoxicillin-clavulanate", 6565, 3435, 52.0),
    ("ampicillin", 13371, 11357, 85.0), ("cefepime", 12699, 6862, 54.0),
    ("cefotaxime", 14485, 10377, 72.0), ("ciprofloxacin", 15064, 11037, 73.0),
    # Counts printed, percentage greyed out.
    ("colistin", 4293, 1, None),
    ("ertapenem", 3931, 814, 21.0), ("gentamicin", 7885, 2323, 29.0),
    ("imipenem", 15254, 2350, 15.0), ("meropenem", 5938, 895, 15.0),
    # The two cells whose numerator repeats the denominator.
    ("piperacillin-tazobactam", 2937, 2937, 29.0),
    ("cotrimoxazole", 8918, 8918, 59.0),
    ("nitrofurantoin", 16229, 1725, 11.0), ("fosfomycin", 855, 58, 7.0),
    ("cefuroxime", 3257, 2581, 79.0),
]))


# --- 2022-2024: Number Tested, %R and a 95% CI, and no numerator -------------
# Read the same way as the tables above. Where a drug is not tested for a
# specimen these editions print "x" rather than greying the block out; those
# cells carry no figures and are not listed here, for the same reason a greyed
# block is not.
HAND_READ_CI: dict = {}
HAND_READ_CI.update(_ci_cells(2022, SA, BLOOD, [
    ("cefoxitin", 5711, 59.0, 57.9, 60.4), ("ciprofloxacin", 5555, 56.0, 55.2, 57.8),
    ("clindamycin", 5947, 35.0, 33.7, 36.1), ("doxycycline", 5264, 15.0, 14.2, 16.2),
    ("erythromycin", 5880, 67.0, 65.8, 68.2), ("gentamicin", 5489, 29.0, 27.8, 30.3),
    ("linezolid", 5827, 0.0, 0.0, 0.1), ("cotrimoxazole", 5313, 38.0, 36.4, 39.0),
    ("teicoplanin", 525, 2.0, 0.8, 3.3),
]))
HAND_READ_CI.update(_ci_cells(2022, SA, PUS_ASPIRATE, [
    ("cefoxitin", 9530, 53.0, 51.5, 53.5), ("ciprofloxacin", 8788, 62.0, 61.3, 63.3),
    ("clindamycin", 10034, 20.0, 19.1, 20.7), ("doxycycline", 7842, 9.0, 8.8, 10.1),
    ("erythromycin", 9824, 56.0, 54.8, 56.7), ("gentamicin", 9128, 25.0, 24.0, 25.7),
    # Printed to two decimals here and to none in the other two columns.
    ("linezolid", 9873, 0.01, 0.0, 0.1), ("cotrimoxazole", 8968, 20.0, 19.6, 21.3),
    ("teicoplanin", 621, 3.0, 1.7, 4.4),
]))
HAND_READ_CI.update(_ci_cells(2022, SA, OSBF, [
    ("cefoxitin", 688, 47.0, 43.0, 50.6), ("ciprofloxacin", 619, 49.0, 45.3, 53.3),
    ("clindamycin", 722, 28.0, 24.4, 31.0), ("doxycycline", 601, 13.0, 10.1, 15.6),
    ("erythromycin", 716, 64.0, 59.9, 67.1), ("gentamicin", 671, 23.0, 19.9, 26.4),
    ("linezolid", 706, 0.0, 0.0, 0.1), ("cotrimoxazole", 619, 32.0, 28.2, 35.7),
    ("teicoplanin", 81, 2.0, 0.4, 9.5),
]))
HAND_READ_CI.update(_ci_cells(2022, EC, BLOOD, [
    ("amikacin", 1952, 27.0, 25.3, 29.4),
    ("amoxicillin-clavulanate", 1054, 57.0, 53.5, 59.6),
    ("ampicillin", 1725, 82.0, 80.4, 84.1), ("cefepime", 1920, 63.0, 60.6, 65.0),
    ("cefotaxime", 1876, 76.0, 74.1, 78.0), ("ciprofloxacin", 2069, 64.0, 62.1, 66.2),
    ("colistin", 1683, 0.0, 0.0, 0.1), ("ertapenem", 603, 43.0, 39.0, 47.0),
    ("gentamicin", 1788, 37.0, 34.8, 39.4), ("imipenem", 1983, 31.0, 29.4, 33.6),
    ("meropenem", 1227, 28.0, 25.5, 30.6),
    ("piperacillin-tazobactam", 1887, 37.0, 34.8, 39.2),
    ("cotrimoxazole", 1909, 54.0, 51.8, 56.4),
]))
HAND_READ_CI.update(_ci_cells(2022, EC, PUS_ASPIRATE, [
    ("amikacin", 6826, 24.0, 22.6, 24.6),
    ("amoxicillin-clavulanate", 4108, 59.0, 57.0, 60.1),
    ("ampicillin", 5692, 89.0, 87.6, 89.3), ("cefepime", 6491, 64.0, 62.9, 65.3),
    ("cefotaxime", 6581, 80.0, 78.8, 80.7), ("ciprofloxacin", 6721, 75.0, 74.2, 76.3),
    ("colistin", 4286, 0.1, 0.0, 0.2), ("ertapenem", 1275, 33.0, 30.5, 35.7),
    ("gentamicin", 5762, 34.0, 33.0, 35.5), ("imipenem", 6633, 28.0, 26.5, 28.7),
    ("meropenem", 4523, 21.0, 19.9, 22.3),
    ("piperacillin-tazobactam", 6194, 36.0, 34.6, 37.0),
    ("cotrimoxazole", 6715, 59.0, 57.3, 59.7),
    # The interval is printed with a space after the dash, "31.2- 38.2".
    ("doxycycline", 722, 35.0, 31.2, 38.2),
]))
HAND_READ_CI.update(_ci_cells(2022, EC, OSBF, [
    ("amikacin", 1170, 24.0, 21.7, 26.7),
    ("amoxicillin-clavulanate", 677, 61.0, 57.7, 65.1),
    ("ampicillin", 1051, 88.0, 85.5, 89.5), ("cefepime", 1257, 67.0, 64.5, 69.8),
    ("cefotaxime", 1234, 81.0, 78.6, 83.1), ("ciprofloxacin", 1276, 76.0, 73.7, 78.5),
    ("colistin", 1080, 0.0, 0.0, 0.1), ("ertapenem", 335, 44.0, 38.2, 49.1),
    ("gentamicin", 917, 34.0, 31.0, 37.2), ("imipenem", 1289, 32.0, 29.8, 35.0),
    ("meropenem", 652, 27.0, 23.8, 30.8),
    ("piperacillin-tazobactam", 1121, 41.0, 37.7, 43.5),
    ("cotrimoxazole", 1260, 59.0, 56.4, 61.9),
    # Printed "24.2- 4.02": the upper bound is below the lower one.
    ("doxycycline", 139, 32.0, 24.2, 4.02),
]))
HAND_READ_CI.update(_ci_cells(2022, EC, URINE, [
    ("amikacin", 17259, 19.0, 18.8, 20.0),
    ("amoxicillin-clavulanate", 10955, 49.0, 47.9, 49.8),
    ("ampicillin", 19886, 86.0, 85.7, 86.6), ("cefepime", 20423, 58.0, 57.4, 58.8),
    ("cefotaxime", 23247, 75.0, 74.1, 75.2),
    ("ciprofloxacin", 23227, 74.0, 72.9, 74.1),
    ("colistin", 7589, 0.01, 0.0, 0.1), ("ertapenem", 4520, 32.0, 30.7, 33.5),
    ("gentamicin", 11518, 27.0, 26.1, 27.7), ("imipenem", 21065, 21.0, 20.5, 21.6),
    ("meropenem", 8814, 18.0, 16.9, 18.5),
    ("piperacillin-tazobactam", 14039, 24.0, 23.1, 24.5),
    ("cotrimoxazole", 23163, 58.0, 57.3, 58.6),
    ("nitrofurantoin", 24953, 9.0, 8.9, 9.6), ("fosfomycin", 4978, 3.0, 2.3, 3.2),
    ("cefuroxime", 6707, 75.0, 73.6, 75.7),
]))
HAND_READ_CI.update(_ci_cells(2023, SA, BLOOD, [
    ("cefoxitin", 4538, 55.0, 53.7, 56.6), ("ciprofloxacin", 4519, 54.0, 52.2, 55.1),
    ("clindamycin", 5074, 38.0, 37.1, 39.8), ("doxycycline", 4553, 10.0, 9.5, 11.3),
    ("erythromycin", 4878, 64.0, 62.2, 64.9), ("gentamicin", 4484, 20.0, 19.2, 21.5),
    # 0 printed beside an interval that starts at 0.1.
    ("linezolid", 4896, 0.0, 0.1, 0.4), ("cotrimoxazole", 4206, 28.0, 26.5, 29.2),
    ("teicoplanin", 943, 4.0, 3.1, 5.8),
]))
HAND_READ_CI.update(_ci_cells(2023, SA, PUS_ASPIRATE, [
    ("cefoxitin", 10146, 54.0, 53.0, 55.0), ("ciprofloxacin", 9473, 69.0, 67.6, 69.5),
    ("clindamycin", 10853, 28.0, 27.6, 29.3), ("doxycycline", 9097, 8.0, 7.9, 9.1),
    ("erythromycin", 10258, 54.0, 53.0, 54.9),
    ("gentamicin", 9574, 21.0, 20.3, 22.0),
    ("linezolid", 10673, 0.02, 0.0, 0.1), ("cotrimoxazole", 8839, 19.0, 18.5, 20.2),
    ("teicoplanin", 1565, 6.0, 4.8, 7.3),
]))
HAND_READ_CI.update(_ci_cells(2023, SA, OSBF, [
    ("cefoxitin", 650, 45.0, 41.1, 48.8), ("ciprofloxacin", 625, 57.0, 53.0, 60.9),
    ("clindamycin", 692, 30.0, 26.6, 33.5), ("doxycycline", 612, 12.0, 9.8, 15.2),
    ("erythromycin", 682, 54.0, 50.4, 58.0), ("gentamicin", 654, 22.0, 19.4, 25.9),
    ("linezolid", 702, 0.0, 0.0, 0.7), ("cotrimoxazole", 589, 27.0, 23.2, 30.5),
    ("teicoplanin", 147, 3.0, 1.3, 8.2),
]))
HAND_READ_CI.update(_ci_cells(2023, EC, BLOOD, [
    ("ampicillin", 1901, 87.0, 85.9, 88.9),
    ("amoxicillin-clavulanate", 1678, 70.0, 67.4, 71.8),
    ("piperacillin-tazobactam", 2317, 48.0, 46.0, 50.1),
    ("ceftriaxone", 1114, 80.0, 77.4, 82.2), ("cefotaxime", 1986, 82.0, 80.3, 83.7),
    ("cefepime", 2430, 67.0, 65.5, 69.2), ("ertapenem", 1007, 47.0, 43.8, 50.0),
    ("imipenem", 2314, 39.0, 37.1, 41.1), ("meropenem", 1907, 36.0, 34.3, 38.7),
    ("amikacin", 2489, 33.0, 31.0, 34.8), ("gentamicin", 2266, 40.0, 38.3, 42.3),
    ("ciprofloxacin", 2427, 72.0, 70.0, 73.6),
    ("cotrimoxazole", 2176, 57.0, 54.6, 58.8), ("colistin", 1858, 0.16, 0.0, 0.5),
]))
HAND_READ_CI.update(_ci_cells(2023, EC, PUS_ASPIRATE, [
    ("ampicillin", 7372, 88.0, 87.9, 90.7),
    ("amoxicillin-clavulanate", 6048, 69.0, 66.6, 71.2),
    ("piperacillin-tazobactam", 7240, 44.0, 38.9, 46.8),
    ("ceftriaxone", 3945, 76.0, 73.8, 77.2), ("cefotaxime", 7728, 81.0, 79.8, 84.3),
    ("cefepime", 8239, 64.0, 59.7, 64.6), ("ertapenem", 2594, 38.0, 34.5, 43.0),
    ("imipenem", 7443, 28.0, 26.2, 31.6), ("meropenem", 6345, 25.0, 22.7, 28.4),
    ("amikacin", 8041, 28.0, 24.1, 28.0), ("gentamicin", 7088, 36.0, 31.1, 38.7),
    ("ciprofloxacin", 7797, 78.0, 75.7, 79.3),
    ("cotrimoxazole", 7268, 58.0, 55.2, 59.5), ("colistin", 5333, 0.0, 0.0, 0.1),
    ("doxycycline", 2080, 41.0, 37.5, 42.8),
]))
HAND_READ_CI.update(_ci_cells(2023, EC, OSBF, [
    ("ampicillin", 1484, 88.0, 86.4, 89.7),
    ("amoxicillin-clavulanate", 1088, 73.0, 70.0, 75.4),
    ("piperacillin-tazobactam", 1428, 45.0, 42.6, 47.9),
    ("ceftriaxone", 705, 81.0, 77.9, 83.8), ("cefotaxime", 1495, 82.0, 79.8, 83.8),
    ("cefepime", 1646, 64.0, 61.8, 66.5), ("ertapenem", 617, 44.0, 40.5, 48.4),
    ("imipenem", 1576, 33.0, 30.3, 35.0), ("meropenem", 1187, 29.0, 26.2, 31.4),
    ("amikacin", 1622, 26.0, 24.0, 28.3), ("gentamicin", 1400, 35.0, 32.3, 37.4),
    ("ciprofloxacin", 1620, 80.0, 77.5, 81.5),
    ("cotrimoxazole", 1447, 60.0, 57.5, 62.7), ("colistin", 1255, 0.48, 0.2, 1.1),
    ("doxycycline", 524, 48.0, 43.7, 52.5),
]))
HAND_READ_CI.update(_ci_cells(2023, EC, URINE, [
    ("ampicillin", 24992, 86.0, 85.7, 86.5),
    ("amoxicillin-clavulanate", 19583, 56.0, 55.0, 56.4),
    ("piperacillin-tazobactam", 21645, 30.0, 29.4, 30.6),
    ("ceftriaxone", 11107, 70.0, 68.7, 70.4),
    ("cefotaxime", 27068, 75.0, 74.9, 76.0),
    ("cefepime", 27750, 56.0, 55.3, 56.5), ("ertapenem", 11009, 27.0, 26.1, 27.8),
    ("imipenem", 27319, 21.0, 20.6, 21.6), ("meropenem", 19903, 17.0, 16.4, 17.5),
    ("amikacin", 25503, 22.0, 21.9, 23.0), ("gentamicin", 20430, 30.0, 28.9, 30.2),
    ("ciprofloxacin", 28791, 76.0, 75.4, 76.4),
    ("cotrimoxazole", 27596, 57.0, 56.2, 57.4),
    # Printed "0.10".
    ("colistin", 12069, 0.1, 0.1, 0.2),
    ("fosfomycin", 12771, 4.0, 3.7, 4.4),
    ("nitrofurantoin", 30769, 16.0, 15.9, 16.7),
]))
HAND_READ_CI.update(_ci_cells(2024, SA, BLOOD, [
    ("cefoxitin", 5967, 56.0, 54.7, 57.3), ("ciprofloxacin", 5801, 54.0, 52.5, 55.0),
    ("clindamycin", 6367, 40.0, 39.1, 41.5), ("doxycycline", 4954, 11.0, 10.3, 12.1),
    ("erythromycin", 6248, 64.0, 63.1, 65.5), ("gentamicin", 5055, 18.0, 17.1, 19.2),
    ("linezolid", 6282, 0.06, 0.05, 0.1), ("cotrimoxazole", 5400, 32.0, 31.0, 33.5),
    ("teicoplanin", 1249, 9.0, 8.0, 11.3),
]))
HAND_READ_CI.update(_ci_cells(2024, SA, PUS_ASPIRATE, [
    ("cefoxitin", 13694, 54.0, 53.2, 54.9),
    ("ciprofloxacin", 13269, 69.0, 68.0, 69.6),
    ("clindamycin", 14596, 29.0, 28.2, 29.6),
    ("doxycycline", 10650, 6.0, 5.7, 6.7),
    ("erythromycin", 14354, 53.0, 52.6, 54.3),
    ("gentamicin", 11675, 18.0, 17.8, 19.2),
    # A zero-width interval, printed 0.0-0.0.
    ("linezolid", 14109, 0.0, 0.0, 0.0),
    ("cotrimoxazole", 12004, 20.0, 19.5, 20.9),
    ("teicoplanin", 2250, 8.0, 6.7, 9.0),
]))
HAND_READ_CI.update(_ci_cells(2024, SA, OSBF, [
    ("cefoxitin", 962, 49.0, 45.5, 51.9), ("ciprofloxacin", 917, 57.0, 54.1, 60.6),
    ("clindamycin", 923, 37.0, 34.1, 40.4), ("doxycycline", 761, 10.0, 7.9, 12.3),
    ("erythromycin", 937, 56.0, 53.1, 59.5), ("gentamicin", 815, 19.0, 16.5, 22.0),
    ("linezolid", 990, 0.0, 0.0, 0.0), ("cotrimoxazole", 835, 28.0, 24.6, 30.7),
    ("teicoplanin", 231, 5.0, 2.5, 8.6),
]))
HAND_READ_CI.update(_ci_cells(2024, EC, BLOOD, [
    ("ampicillin", 2278, 86.0, 85.0, 87.8),
    ("amoxicillin-clavulanate", 2759, 68.0, 66.0, 69.5),
    ("piperacillin-tazobactam", 3239, 52.0, 50.3, 53.7),
    ("ceftriaxone", 2420, 80.0, 78.6, 81.8), ("cefotaxime", 2078, 81.0, 79.0, 82.5),
    ("cefepime", 2714, 69.0, 67.5, 71.0), ("ertapenem", 1634, 49.0, 46.2, 51.1),
    ("imipenem", 3062, 40.0, 37.9, 41.4), ("meropenem", 2667, 36.0, 34.1, 37.8),
    ("amikacin", 3254, 37.0, 35.5, 38.9), ("gentamicin", 2797, 41.0, 39.1, 42.8),
    ("ciprofloxacin", 3129, 74.0, 72.6, 75.7),
    ("cotrimoxazole", 2748, 56.0, 54.6, 58.3), ("colistin", 2351, 0.09, 0.0, 0.3),
]))
HAND_READ_CI.update(_ci_cells(2024, EC, PUS_ASPIRATE, [
    ("ampicillin", 8491, 89.0, 87.2, 89.9),
    ("amoxicillin-clavulanate", 9744, 63.0, 61.3, 65.4),
    ("piperacillin-tazobactam", 11220, 49.0, 48.1, 50.9),
    ("ceftriaxone", 8687, 80.0, 78.4, 81.0), ("cefotaxime", 9635, 81.0, 79.6, 82.2),
    ("cefepime", 9944, 60.0, 58.9, 62.0), ("ertapenem", 6225, 34.0, 31.6, 36.3),
    ("imipenem", 10316, 28.0, 26.3, 30.1), ("meropenem", 10297, 28.0, 26.1, 29.2),
    ("amikacin", 11405, 29.0, 27.9, 30.8), ("gentamicin", 9845, 34.0, 32.9, 36.1),
    ("ciprofloxacin", 11149, 77.0, 75.0, 77.2),
    ("cotrimoxazole", 10466, 58.0, 55.5, 59.6), ("colistin", 7605, 0.04, 0.0, 0.2),
    # The same three figures the 2023 edition prints for this cell.
    ("doxycycline", 2080, 41.0, 37.5, 42.8),
]))
HAND_READ_CI.update(_ci_cells(2024, EC, OSBF, [
    ("ampicillin", 1490, 89.0, 87.5, 90.7),
    ("amoxicillin-clavulanate", 1638, 71.0, 68.4, 72.9),
    ("piperacillin-tazobactam", 2019, 55.0, 53.1, 57.5),
    ("ceftriaxone", 1383, 83.0, 80.9, 84.9), ("cefotaxime", 1637, 83.0, 80.9, 84.6),
    ("cefepime", 1818, 64.0, 61.4, 65.8), ("ertapenem", 1150, 45.0, 42.1, 47.9),
    ("imipenem", 1853, 38.0, 35.6, 40.0), ("meropenem", 1796, 34.0, 31.9, 36.3),
    ("amikacin", 2064, 27.0, 25.1, 29.0), ("gentamicin", 1737, 33.0, 30.7, 35.1),
    ("ciprofloxacin", 1988, 78.0, 76.4, 80.1),
    ("cotrimoxazole", 1920, 62.0, 59.8, 64.2), ("colistin", 1381, 0.07, 0.0, 0.5),
    ("doxycycline", 813, 49.0, 45.1, 52.1),
]))
HAND_READ_CI.update(_ci_cells(2024, EC, URINE, [
    ("ampicillin", 30771, 87.0, 84.7, 89.3),
    ("amoxicillin-clavulanate", 31408, 59.0, 57.2, 63.4),
    ("piperacillin-tazobactam", 34001, 40.0, 37.3, 43.8),
    ("ceftriaxone", 22108, 74.0, 69.8, 76.7),
    ("cefotaxime", 34490, 76.0, 73.3, 78.0),
    ("cefepime", 28581, 54.0, 50.8, 56.7), ("ertapenem", 17191, 25.0, 22.2, 29.9),
    ("imipenem", 32038, 23.0, 21.6, 25.9), ("meropenem", 26633, 20.0, 16.7, 22.6),
    ("amikacin", 34617, 25.0, 23.6, 29.1), ("gentamicin", 30890, 32.0, 30.0, 38.5),
    ("ciprofloxacin", 36167, 73.0, 70.9, 78.6),
    ("cotrimoxazole", 37565, 55.0, 53.0, 59.4),
    ("colistin", 20173, 0.035, 0.0, 0.5),
    ("fosfomycin", 21602, 4.0, 3.2, 5.6),
    ("nitrofurantoin", 41460, 19.0, 16.9, 20.3),
]))


# Cells where the printed percentage does not follow from the printed counts,
# read off the same pages. Seven sit just past the half-point of the printed
# precision, which is the source rounding a percentage it did not compute from
# the counts it printed. The eighth is a different animal: 24 resistant of 2,638
# is 0.9%, not the 12% printed beside it.
#
# All eight are in 2019 and 2020. Every 2021 cell whose numerator is its own
# reconciles, so the 2021 edition adds nothing here -- its fifteen problem cells
# are recorded as corrupt numerators instead, which is a different statement and
# is checked separately below.
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
def test_every_hand_read_ci_cell_matches(narsnet_records):
    """The 2022-2024 counterpart: Number Tested, %R and both interval bounds."""
    index = _index(narsnet_records)
    wrong = []
    for key, expected in sorted(HAND_READ_CI.items(), key=str):
        rec = index.get(key)
        if rec is None:
            wrong.append("{}: no record extracted".format(key))
            continue
        got = (rec.tested_n, rec.resistant_pct, rec.ci_low, rec.ci_high)
        if got != expected:
            wrong.append("{}: hand-read {}, parsed {}".format(key, expected, got))
    assert not wrong, "\n".join(wrong)


@needs_pdfs
def test_no_cell_is_extracted_that_was_not_hand_read(narsnet_records):
    """The reverse direction: a phantom row invented by the grid would show up
    here even though every hand-read cell still matched."""
    assert set(_index(narsnet_records)) == set(HAND_READ) | set(HAND_READ_CI)


@needs_pdfs
def test_the_two_hand_read_sets_do_not_overlap(narsnet_records):
    """No edition prints both a numerator and an interval, so no cell belongs to
    both dictionaries."""
    assert not set(HAND_READ) & set(HAND_READ_CI)
    assert {k[0] for k in HAND_READ} == set(COUNT_YEARS)
    assert {k[0] for k in HAND_READ_CI} == set(CI_YEARS)


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


# --- the 2021 corrupt numerators ---------------------------------------------

# Every cell the parser should mark `corrupt_in_source`, listed here rather than
# derived from CORRUPT_NUMERATORS so that widening a declaration by accident
# fails this test instead of quietly agreeing with itself.
EXPECTED_CORRUPT = {
    (2021, EC, drug, BLOOD)
    for drug in (
        "amikacin", "amoxicillin-clavulanate", "ampicillin", "cefepime",
        "cefotaxime", "ciprofloxacin", "colistin", "ertapenem", "gentamicin",
        "imipenem", "meropenem", "piperacillin-tazobactam", "cotrimoxazole",
    )
} | {
    (2021, EC, "piperacillin-tazobactam", URINE),
    (2021, EC, "cotrimoxazole", URINE),
}


def test_corrupt_declarations_are_scoped_to_one_table():
    """Whatever else changes, this must not start covering another edition or
    another organism by accident."""
    assert {(e.year, e.organism) for e in CORRUPT_NUMERATORS} == {
        (2021, "Escherichia coli")
    }
    assert {e.specimen for e in CORRUPT_NUMERATORS} == {BLOOD, URINE}


def test_a_whole_sub_column_declaration_covers_any_drug():
    """The Blood declaration names no drugs, so it covers the column."""
    for drug in ("amikacin", "meropenem", "colistin"):
        assert find_corrupt_numerators(2021, EC, BLOOD, drug) is not None
    # ... and does not leak into the columns beside it, or into other editions.
    assert find_corrupt_numerators(2021, EC, PUS_ASPIRATE, "meropenem") is None
    assert find_corrupt_numerators(2021, EC, OSBF, "meropenem") is None
    assert find_corrupt_numerators(2020, EC, BLOOD, "imipenem") is None
    assert find_corrupt_numerators(2021, SA, BLOOD, "cefoxitin") is None


def test_a_named_cell_declaration_covers_only_those_cells():
    assert find_corrupt_numerators(2021, EC, URINE, "cotrimoxazole") is not None
    assert (
        find_corrupt_numerators(2021, EC, URINE, "piperacillin-tazobactam")
        is not None
    )
    assert find_corrupt_numerators(2021, EC, URINE, "nitrofurantoin") is None


@needs_pdfs
def test_exactly_the_declared_cells_are_marked_corrupt(narsnet_records):
    seen = {
        (r.source_report_year, r.organism, r.antibiotic, r.specimen)
        for r in narsnet_records
        if r.numerator_status == NUMERATOR_CORRUPT
    }
    assert seen == EXPECTED_CORRUPT


@needs_pdfs
def test_a_corrupt_numerator_is_carried_as_printed_and_never_used(narsnet_records):
    """The figure is kept exactly as the page prints it -- 981 resistant of 854
    tested -- and nothing is computed from it."""
    rec = _index(narsnet_records)[(2021, EC, "meropenem", BLOOD)]
    assert (rec.tested_n, rec.resistant_n, rec.resistant_pct) == (854, 981, 25.0)
    assert rec.numerator_status == NUMERATOR_CORRUPT
    assert rec.reconcilable is False
    assert rec.computed_pct is None
    assert "numerator_corrupt_in_source" in rec.flags
    # No pct_mismatch: there is no numerator of its own to disagree with.
    assert not [f for f in rec.flags if f.startswith("pct_mismatch")]


@needs_pdfs
def test_a_urine_numerator_that_repeats_its_denominator(narsnet_records):
    for drug, count, pct in (
        ("piperacillin-tazobactam", 2937, 29.0),
        ("cotrimoxazole", 8918, 59.0),
    ):
        rec = _index(narsnet_records)[(2021, EC, drug, URINE)]
        assert rec.tested_n == rec.resistant_n == count
        assert rec.resistant_pct == pct
        assert rec.numerator_status == NUMERATOR_CORRUPT
        assert rec.reconcilable is False


@needs_pdfs
def test_the_columns_beside_the_corrupt_one_are_untouched(narsnet_records):
    """Pus aspirate and OSBF reconcile throughout the same table, which is what
    makes the Blood sub-column, rather than the table, the thing at issue."""
    for specimen in (PUS_ASPIRATE, OSBF):
        rows = [
            r for r in narsnet_records
            if r.source_report_year == 2021 and r.organism == EC
            and r.specimen == specimen
        ]
        assert len(rows) == 14
        assert all(r.numerator_status == NUMERATOR_PRINTED for r in rows)
        assert all(r.reconcilable for r in rows)
        assert not [f for r in rows for f in r.flags if f.startswith("pct_mismatch")]


@needs_pdfs
def test_the_2021_s_aureus_table_reconciles_throughout(narsnet_records):
    rows = [
        r for r in narsnet_records
        if r.source_report_year == 2021 and r.organism == SA
    ]
    assert len(rows) == 27
    assert all(r.numerator_status == NUMERATOR_PRINTED for r in rows)
    assert all(not r.flags for r in rows)


@needs_pdfs
def test_two_corrupt_cells_agree_with_their_own_printed_percentage(narsnet_records):
    """Amoxicillin-clavulanate prints 390 of 680 beside 57, and colistin 0 of
    914 beside 0. Both agree. They are still marked corrupt: the declaration is
    scoped to the sub-column, and the agreements are counted in the extraction
    report rather than exempted here."""
    index = _index(narsnet_records)
    for drug, tested, resistant, pct in (
        ("amoxicillin-clavulanate", 680, 390, 57.0),
        ("colistin", 914, 0, 0.0),
    ):
        rec = index[(2021, EC, drug, BLOOD)]
        assert (rec.tested_n, rec.resistant_n, rec.resistant_pct) == (
            tested, resistant, pct,
        )
        assert abs(100.0 * resistant / tested - pct) <= 0.5
        assert rec.numerator_status == NUMERATOR_CORRUPT
        assert rec.reconcilable is False


@needs_pdfs
def test_the_2021_greyed_blocks_emit_no_row(narsnet_records):
    """Nitrofurantoin, fosfomycin and cefuroxime are printed for urine only;
    doxycycline for pus aspirate and OSBF only. The other blocks are greyed out
    entirely, so nothing is emitted for them."""
    by_drug = {}
    for r in narsnet_records:
        if r.source_report_year == 2021 and r.organism == EC:
            by_drug.setdefault(r.antibiotic, set()).add(r.specimen)
    assert by_drug["nitrofurantoin"] == {URINE}
    assert by_drug["fosfomycin"] == {URINE}
    assert by_drug["cefuroxime"] == {URINE}
    assert by_drug["doxycycline"] == {PUS_ASPIRATE, OSBF}


@needs_pdfs
def test_the_2021_suppressed_percentage_is_not_read_as_zero(narsnet_records):
    """E. coli colistin, urine: both counts printed, percentage greyed out."""
    rec = _index(narsnet_records)[(2021, EC, "colistin", URINE)]
    assert (rec.tested_n, rec.resistant_n) == (4293, 1)
    assert rec.resistant_pct is None
    assert "pct_suppressed_in_source" in rec.flags
    assert rec.numerator_status == NUMERATOR_PRINTED


# --- the 2022-2024 editions: no numerator, an interval instead --------------


@needs_pdfs
def test_the_ci_editions_print_no_numerator_at_all(narsnet_records):
    """Not one row of 2022-2024 carries a numerator, so none is reconcilable and
    none has a computed percentage. A numerator is never back-computed from the
    denominator and the percentage: it would be the only invented count in the
    repo, and checking the percentage against it would be circular."""
    rows = [r for r in narsnet_records if r.source_report_year in CI_YEARS]
    assert len(rows) == 258
    assert {r.numerator_status for r in rows} == {NUMERATOR_NOT_PRINTED}
    assert {r.resistant_n for r in rows} == {None}
    assert {r.reconcilable for r in rows} == {False}
    assert {r.computed_pct for r in rows} == {None}
    assert all("numerator_not_printed_in_source" in r.flags for r in rows)


@needs_pdfs
def test_the_confidence_interval_arrives_in_2022_and_not_before(narsnet_records):
    for r in narsnet_records:
        if r.source_report_year in CI_YEARS:
            assert r.ci_low is not None and r.ci_high is not None, r
        else:
            assert r.ci_low is None and r.ci_high is None, r


@needs_pdfs
def test_an_interval_printed_with_a_space_is_read_as_one_cell(narsnet_records):
    """2022 E. coli, doxycycline, pus aspirate prints "31.2- 38.2", which
    arrives as two words. Reading only the first would lose the upper bound."""
    rec = _index(narsnet_records)[(2022, EC, "doxycycline", PUS_ASPIRATE)]
    assert (rec.ci_low, rec.ci_high) == (31.2, 38.2)


@needs_pdfs
def test_exactly_two_rows_sit_outside_their_own_interval(narsnet_records):
    seen = {
        (r.source_report_year, r.organism, r.antibiotic, r.specimen)
        for r in narsnet_records
        if any(f.startswith("ci_excludes_point_estimate") for f in r.flags)
    }
    assert seen == {
        (2022, EC, "doxycycline", OSBF),
        (2023, SA, "linezolid", BLOOD),
    }


@needs_pdfs
def test_the_2023_linezolid_blood_row_is_caught(narsnet_records):
    """4,896 tested, a point estimate of 0, and an interval of 0.1-0.4. The
    percentage column is printed to whole numbers and the interval to one
    decimal, and the chapter gives the year's figure as 0.2%, which the interval
    brackets and which rounds to the printed 0. Carried exactly as printed."""
    rec = _index(narsnet_records)[(2023, SA, "linezolid", BLOOD)]
    assert (rec.tested_n, rec.resistant_pct) == (4896, 0.0)
    assert (rec.ci_low, rec.ci_high) == (0.1, 0.4)
    assert any(f.startswith("ci_excludes_point_estimate") for f in rec.flags)
    assert not [f for f in rec.flags if f.startswith("ci_bounds_inverted")]


@needs_pdfs
def test_an_interval_printed_in_reverse_order_is_kept_that_way(narsnet_records):
    """2022 E. coli, doxycycline, OSBF prints "24.2- 4.02". The bounds are used
    as printed rather than swapped, because swapping them would be a repair."""
    rec = _index(narsnet_records)[(2022, EC, "doxycycline", OSBF)]
    assert (rec.tested_n, rec.resistant_pct) == (139, 32.0)
    assert (rec.ci_low, rec.ci_high) == (24.2, 4.02)
    assert rec.ci_high < rec.ci_low
    assert any(f.startswith("ci_bounds_inverted") for f in rec.flags)
    assert any(f.startswith("ci_excludes_point_estimate") for f in rec.flags)


@needs_pdfs
def test_the_2023_panel_swap_keeps_the_panel_size(narsnet_records):
    """Cefuroxime leaves the E. coli panel and ceftriaxone joins it, and the
    panel is seventeen drugs on both sides. A check on panel size alone would
    see nothing here."""
    panels = {}
    for r in narsnet_records:
        if r.organism == EC:
            panels.setdefault(r.source_report_year, set()).add(r.antibiotic)
    assert len(panels[2022]) == len(panels[2023]) == 17
    assert panels[2022] - panels[2023] == {"cefuroxime"}
    assert panels[2023] - panels[2022] == {"ceftriaxone"}
    assert panels[2023] == panels[2024]


@needs_pdfs
def test_x_marked_cells_emit_no_row(narsnet_records):
    """From 2022 the reports print "x" where a drug is not tested for a
    specimen, with a footnote saying so, rather than greying the block. Nothing
    was measured, so nothing is emitted -- the same treatment a greyed block
    gets in the earlier editions."""
    by_drug = {}
    for r in narsnet_records:
        if r.organism == EC and r.source_report_year == 2022:
            by_drug.setdefault(r.antibiotic, set()).add(r.specimen)
    assert by_drug["nitrofurantoin"] == {URINE}
    assert by_drug["fosfomycin"] == {URINE}
    assert by_drug["cefuroxime"] == {URINE}
    assert by_drug["doxycycline"] == {PUS_ASPIRATE, OSBF}


@needs_pdfs
def test_the_pus_aspirate_doxycycline_row_repeats_between_2023_and_2024(
    narsnet_records,
):
    """The 2023 and 2024 E. coli tables print the same three figures for this one
    cell. It is recorded rather than flagged: both editions are carried as
    printed, and the reading is left to a reader who can see that every other
    denominator in that column changes between the two."""
    index = _index(narsnet_records)
    a = index[(2023, EC, "doxycycline", PUS_ASPIRATE)]
    b = index[(2024, EC, "doxycycline", PUS_ASPIRATE)]
    assert (a.tested_n, a.resistant_pct, a.ci_low, a.ci_high) == (
        2080, 41.0, 37.5, 42.8,
    )
    assert (b.tested_n, b.resistant_pct, b.ci_low, b.ci_high) == (
        a.tested_n, a.resistant_pct, a.ci_low, a.ci_high,
    )
    others_2023 = {
        r.antibiotic: r.tested_n
        for r in narsnet_records
        if r.organism == EC and r.source_report_year == 2023
        and r.specimen == PUS_ASPIRATE
    }
    others_2024 = {
        r.antibiotic: r.tested_n
        for r in narsnet_records
        if r.organism == EC and r.source_report_year == 2024
        and r.specimen == PUS_ASPIRATE
    }
    same = {d for d in others_2023 if others_2023[d] == others_2024.get(d)}
    assert same == {"doxycycline"}


@needs_pdfs
def test_provenance_is_carried_on_every_row(narsnet_records):
    for r in narsnet_records:
        assert r.network == "narsnet"
        assert r.year == r.source_report_year
        assert r.source_url.startswith("https://ncdc.mohfw.gov.in/uploads/pdf/")
        assert r.source_table.startswith("Table ")
        # 2019 and 2020 are exactly the two editions whose cover year is not
        # their reporting period; every later cover agrees with its own period.
        assert r.source_cover_year == {
            2019: 2020, 2020: 2021, 2021: None,
            2022: None, 2023: None, 2024: None,
        }[r.source_report_year]


@needs_pdfs
def test_reconcilable_tracks_the_printed_numerator(narsnet_records):
    """`reconcilable` is true for exactly one of the three numerator states, so
    a consumer that filters on it can never reach a number it must not use."""
    for r in narsnet_records:
        if r.numerator_status == NUMERATOR_PRINTED:
            assert r.reconcilable is True
            assert r.computed_pct is not None
        else:
            assert r.numerator_status in (NUMERATOR_CORRUPT, NUMERATOR_NOT_PRINTED)
            assert r.reconcilable is False
            assert r.computed_pct is None


@needs_pdfs
def test_the_three_numerator_states_are_all_present_and_distinct(narsnet_records):
    """A corrupt cell prints a number and a not-printed cell does not, which is
    the reason these are two values rather than one value and a flag."""
    by_status = {}
    for r in narsnet_records:
        by_status.setdefault(r.numerator_status, []).append(r)
    assert set(by_status) == {
        NUMERATOR_PRINTED, NUMERATOR_NOT_PRINTED, NUMERATOR_CORRUPT,
    }
    assert all(r.resistant_n is not None for r in by_status[NUMERATOR_CORRUPT])
    assert all(r.resistant_n is None for r in by_status[NUMERATOR_NOT_PRINTED])
