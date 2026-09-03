"""V3 -- NARS-Net drug-label normalisation, and the guarantee it changes nothing.

Two jobs here.

The first is ordinary coverage: every antibiotic label printed in a NARS-Net
E. coli or S. aureus table, in every edition, must resolve to a canonical name.
The label lists below are transcribed from `docs/narsnet_v3_research.md` (A2),
not re-derived from the PDFs -- that document is settled, and a test that
re-read the source would be testing the extractor rather than the vocabulary.

The second is the no-drift guarantee. `antibiotics.normalise_antibiotic` ends in
a substring scan over its whole alias table, so adding NARS-Net names to that
table could silently change how an AMRSN label resolves. V3 therefore keeps its
own table, and `test_amrsn_labels_normalise_identically_without_v3` proves the
point the hard way: it re-normalises every drug name in `data/processed/` in a
subprocess that never imports the V3 module, and compares.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys

import pytest

from src.parsers.antibiotics import ALIASES, normalise_antibiotic
from src.parsers.narsnet_antibiotics import (
    NARSNET_ALIASES,
    normalise_narsnet_antibiotic,
)
from src.sources import REPO_ROOT

# --- printed labels, per edition, from docs/narsnet_v3_research.md A2 --------

E_COLI_PANELS = {
    2017: [
        "Ampicillin", "Cefotaxime", "Ceftazidime", "Cefepime", "Ertapenem",
        "Imipenem", "Ciprofloxacin",
    ],
    2018: [
        "Ampicillin", "Cefotaxime", "Cefepime", "Ertapenem", "Imipenem",
        "Ciprofloxacin", "Trimethoprim/Sulfamethoxazole", "Nitrofurantoin",
    ],
    2019: [
        "Ampicillin", "Cefotaxime", "Cefepime", "Ertapenem", "Imipenem",
        "Ciprofloxacin", "TMP/SMX", "Nitrofurantoin", "Colistin",
    ],
    2020: [
        "Ampicillin", "Cefotaxime", "Cefepime", "Ertapenem", "Imipenem",
        "Ciprofloxacin", "TMP/SMX", "Nitrofurantoin", "Colistin",
    ],
    2021: [
        "Ampicillin", "Cefotaxime", "Cefepime", "Ertapenem", "Imipenem",
        "Ciprofloxacin", "TMP / SMX", "Nitrofurantoin", "Colistin", "Amikacin",
        "Amoxicillin/ Clavulanic acid", "Gentamicin", "Meropenem",
        "Piperacillin/ Tazobactam", "Fosfomycin", "Cefuroxime", "Doxycycline",
    ],
    2022: [
        "Ampicillin", "Cefotaxime", "Cefepime", "Ertapenem", "Imipenem",
        "Ciprofloxacin", "TMP/SMX", "Nitrofurantoin", "Colistin", "Amikacin",
        "Amox-clav", "Gentamicin", "Meropenem", "Pip/Taz", "Fosfomycin",
        "Cefuroxime", "Doxycycline",
    ],
    # 2023 drops cefuroxime and adds ceftriaxone -- same count, different set.
    2023: [
        "Ampicillin", "Amox/Clav", "Pip/Taz", "Ceftriaxone", "Cefotaxime",
        "Cefepime", "Ertapenem", "Imipenem", "Meropenem", "Amikacin",
        "Gentamicin", "Ciprofloxacin", "TMP/SMX", "Colistin", "Fosfomycin",
        "Nitrofurantoin", "Doxycycline",
    ],
    2024: [
        "Ampicillin", "Amox-Clav", "Pip-Taz", "Ceftriaxone", "Cefotaxime",
        "Cefepime", "Ertapenem", "Imipenem", "Meropenem", "Amikacin",
        "Gentamicin", "Ciprofloxacin", "TMP-SMX", "Colistin", "Fosfomycin",
        "Nitrofurantoin", "Doxycycline",
    ],
}

S_AUREUS_PANELS = {
    2017: [
        "Cefoxitin", "Erythromycin", "Clindamycin", "TMP/SMX", "Gentamycin",
        "Ciprofloxacin", "Linezolid", "Doxycycline", "Tetracycline",
    ],
    2018: [
        "Cefoxitin", "Erythromycin", "Clindamycin", "TMP/SMX", "Gentamicin",
        "Ciprofloxacin", "Linezolid", "Doxycycline", "Tetracycline",
        "Vancomycin*",
    ],
    2019: [
        "Cefoxitin", "Gentamicin", "Ciprofloxacin", "TMP/SMX", "Clindamycin",
        "Erythromycin", "Linezolid", "Doxycycline",
    ],
    2020: [
        "Cefoxitin", "Gentamicin", "Ciprofloxacin", "TMP/SMX", "Clindamycin",
        "Erythromycin", "Linezolid", "Doxycycline",
    ],
    2021: [
        "Cefoxitin", "Gentamicin", "Ciprofloxacin", "TMP/SMX", "Clindamycin",
        "Erythromycin", "Linezolid", "Doxycycline", "Teicoplanin",
    ],
    2022: [
        "Cefoxitin", "Gentamicin", "Ciprofloxacin", "TMP/SMX", "Clindamycin",
        "Erythromycin", "Linezolid", "Doxycycline", "Teicoplanin",
    ],
    2023: [
        "Cefoxitin", "Ciprofloxacin", "Clindamycin", "Doxycycline",
        "Erythromycin", "Gentamicin", "Linezolid*", "TMP/SMX", "Teicoplanin",
    ],
    2024: [
        "Cefoxitin", "Ciprofloxacin", "Clindamycin", "Doxycycline",
        "Erythromycin", "Gentamicin", "Linezolid*", "TMP-SMX", "Teicoplanin",
    ],
}

PANEL_SIZES_E_COLI = {2017: 7, 2018: 8, 2019: 9, 2020: 9, 2021: 17, 2022: 17,
                      2023: 17, 2024: 17}
PANEL_SIZES_S_AUREUS = {2017: 9, 2018: 10, 2019: 8, 2020: 8, 2021: 9, 2022: 9,
                        2023: 9, 2024: 9}


PANELS_BY_ORGANISM = {
    "Escherichia coli": E_COLI_PANELS,
    "Staphylococcus aureus": S_AUREUS_PANELS,
}

PANELS = [
    (organism, year)
    for organism, panels in PANELS_BY_ORGANISM.items()
    for year in sorted(panels)
]


# --- coverage ---------------------------------------------------------------


@pytest.mark.parametrize("organism,year", PANELS)
def test_every_printed_label_in_a_panel_resolves(organism, year):
    labels = PANELS_BY_ORGANISM[organism][year]
    unresolved = [
        label for label in labels if normalise_narsnet_antibiotic(label) is None
    ]
    assert not unresolved, "{} {}: {} did not normalise".format(
        year, organism, unresolved
    )


@pytest.mark.parametrize("year,expected", sorted(PANEL_SIZES_E_COLI.items()))
def test_e_coli_panel_sizes_match_the_research_record(year, expected):
    assert len(E_COLI_PANELS[year]) == expected
    # 2021-2024 all print 17 drugs, but 2023 is not the same seventeen as 2022.
    assert len(set(map(normalise_narsnet_antibiotic, E_COLI_PANELS[year]))) == expected


@pytest.mark.parametrize("year,expected", sorted(PANEL_SIZES_S_AUREUS.items()))
def test_s_aureus_panel_sizes_match_the_research_record(year, expected):
    assert len(S_AUREUS_PANELS[year]) == expected
    assert len(set(map(normalise_narsnet_antibiotic, S_AUREUS_PANELS[year]))) == expected


def test_the_2023_cefuroxime_ceftriaxone_swap_is_visible_after_normalisation():
    """Both editions print 17 drugs; a size comparison alone would miss this."""
    y2022 = set(map(normalise_narsnet_antibiotic, E_COLI_PANELS[2022]))
    y2023 = set(map(normalise_narsnet_antibiotic, E_COLI_PANELS[2023]))
    assert y2022 - y2023 == {"cefuroxime"}
    assert y2023 - y2022 == {"ceftriaxone"}


# --- the variants this module exists for ------------------------------------


@pytest.mark.parametrize(
    "label,expected",
    [
        # Abbreviated cotrimoxazole. The 2024 report prints TMP/SMX in Table 6
        # and TMP-SMX in Table 8, so normalisation is per cell, not per edition.
        ("TMP/SMX", "cotrimoxazole"),
        ("TMP-SMX", "cotrimoxazole"),
        ("TMP / SMX", "cotrimoxazole"),
        ("Trimethoprim/Sulfamethoxazole", "cotrimoxazole"),
        ("Trimethoprim/sulfamethoxazole", "cotrimoxazole"),
        # Abbreviated piperacillin-tazobactam.
        ("Pip/Taz", "piperacillin-tazobactam"),
        ("Pip-Taz", "piperacillin-tazobactam"),
        ("Piperacillin/ Tazobactam", "piperacillin-tazobactam"),
        # Amoxicillin-clavulanate, all four printed forms.
        ("Amoxicillin/ Clavulanic acid", "amoxicillin-clavulanate"),
        ("Amox-clav", "amoxicillin-clavulanate"),
        ("Amox/Clav", "amoxicillin-clavulanate"),
        ("Amox-Clav", "amoxicillin-clavulanate"),
        # The 2017 spelling, corrected from 2018 on.
        ("Gentamycin", "gentamicin"),
        ("Gentamicin", "gentamicin"),
        # New canonical names, for drugs no AMRSN panel carries.
        ("Ampicillin", "ampicillin"),
        ("Cefuroxime", "cefuroxime"),
        # Footnote markers must not defeat a lookup.
        ("Linezolid*", "linezolid"),
        ("Vancomycin*", "vancomycin"),
    ],
)
def test_printed_variants_map_to_canonical_names(label, expected):
    assert normalise_narsnet_antibiotic(label) == expected


@pytest.mark.parametrize("label", ["", None, "   ", "N=1234", "Number Tested"])
def test_non_drug_labels_do_not_resolve(label):
    assert normalise_narsnet_antibiotic(label) is None


def test_shared_names_delegate_rather_than_being_redefined():
    """Most of both panels resolves through `antibiotics.py`, so a drug named the
    same by both networks has exactly one canonical definition."""
    shared = [
        "Cefotaxime", "Ceftazidime", "Ceftriaxone", "Cefepime", "Cefoxitin",
        "Ertapenem", "Imipenem", "Meropenem", "Amikacin", "Ciprofloxacin",
        "Colistin", "Doxycycline", "Tetracycline", "Vancomycin", "Teicoplanin",
        "Linezolid", "Erythromycin", "Clindamycin", "Fosfomycin",
        "Nitrofurantoin",
    ]
    for label in shared:
        assert _key_absent_from_narsnet_table(label)
        assert normalise_narsnet_antibiotic(label) == normalise_antibiotic(label)


def _key_absent_from_narsnet_table(label) -> bool:
    from src.parsers.narsnet_antibiotics import _key

    return _key(label) not in NARSNET_ALIASES


# --- no drift on the AMRSN side ---------------------------------------------

# Snapshot of the shared table as V3 found it. If a V3 change ever adds to it,
# this fails first and says so plainly.
EXPECTED_SHARED_ALIAS_COUNT = 37


def test_shared_alias_table_is_untouched_by_v3():
    assert len(ALIASES) == EXPECTED_SHARED_ALIAS_COUNT
    for canonical in ("ampicillin", "cefuroxime", "amoxicillin-clavulanate"):
        assert canonical not in ALIASES.values(), (
            "{!r} is a NARS-Net canonical name and must not be in the shared "
            "table".format(canonical)
        )
    for key in ("tmpsmx", "piptaz", "amoxclav", "gentamycin", "ampicillin",
                "cefuroxime"):
        assert key not in ALIASES


def test_the_two_alias_tables_share_no_keys():
    assert not set(NARSNET_ALIASES) & set(ALIASES)


def _dataset_antibiotics():
    names = set()
    for name in ("amr_trends.csv", "amr_rc_trends.csv"):
        path = REPO_ROOT / "data" / "processed" / name
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row.get("antibiotic"):
                    names.add(row["antibiotic"])
    return sorted(names)


def test_dataset_antibiotics_are_stable_canonical_names():
    names = _dataset_antibiotics()
    assert names, "no antibiotic names found in data/processed/"
    for name in names:
        assert normalise_antibiotic(name) == name


def test_amrsn_labels_normalise_identically_without_v3():
    """The no-drift guarantee, checked rather than asserted.

    A subprocess imports only `antibiotics` -- never the V3 module -- and
    normalises every drug name in `data/processed/`. Its answers must match
    this process's, where the V3 module is imported. If a future edit moved a
    NARS-Net name into the shared table, the substring scan could change one of
    these and the two runs would disagree.
    """
    names = _dataset_antibiotics()
    script = (
        "import json,sys;"
        "from src.parsers.antibiotics import normalise_antibiotic as n;"
        "print(json.dumps({x: n(x) for x in json.loads(sys.argv[1])}))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script, json.dumps(names)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    without_v3 = json.loads(proc.stdout)
    assert "narsnet_antibiotics" not in proc.stderr

    with_v3 = {x: normalise_antibiotic(x) for x in names}
    assert without_v3 == with_v3
