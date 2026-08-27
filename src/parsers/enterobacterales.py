"""Enterobacterales yearly susceptibility trend tables.

Covers the "all samples (except faeces and urine)" trend tables:

    2024 edition -> Table 2.6 (E. coli), Table 2.7 (K. pneumoniae)
    2023 edition -> Table 3.6 (E. coli), Table 3.7 (K. pneumoniae)
    2022 edition -> Table 3.6 (E. coli), Table 3.7 (K. pneumoniae)

Table numbers are discovered from the caption at run time, never assumed --
see the module docstring in `base.py` for why.
"""

from __future__ import annotations

from .antibiotics import normalise_antibiotic  # noqa: F401  (public re-export)
from .trend_parser import OrganismSpec, parse_report as _parse

# Panel as printed in the Enterobacterales trend tables, in table order.
CANONICAL_PANEL = [
    "piperacillin-tazobactam",
    "cefazolin",
    "cefotaxime",
    "ceftazidime",
    "ertapenem",
    "imipenem",
    "meropenem",
    "amikacin",
    "ciprofloxacin",
    "levofloxacin",
]

# Each edition also carries a urine-only trend table with a near-identical
# caption (Tables 2.17/2.18 in 2024, 3.17/3.18 in 2023). Those are rejected.
SPECS = {
    "Escherichia coli": OrganismSpec(
        name="Escherichia coli",
        pattern=r"\b(?:E\.?\s*coli|Escherichia\s+coli)\b",
        panel=CANONICAL_PANEL,
    ),
    "Klebsiella pneumoniae": OrganismSpec(
        name="Klebsiella pneumoniae",
        # The 2022 edition prints "Klebsiella pneumonia" (sic).
        pattern=r"\b(?:K\.?\s*pneumoniae?|Klebsiella\s+pneumoniae?)\b",
        panel=CANONICAL_PANEL,
    ),
}

ORGANISMS = SPECS  # backwards-compatible name


def parse_report(source, organism: str, extracted_date=None):
    if organism not in SPECS:
        raise KeyError(
            "unknown organism {!r}; known: {}".format(organism, sorted(SPECS))
        )
    return _parse(source, SPECS[organism], extracted_date)
