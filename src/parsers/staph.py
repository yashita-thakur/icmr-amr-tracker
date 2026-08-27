"""Staphylococci yearly trend tables.

    2024 edition -> Table 6.4 (S. aureus), Table 6.9 (MRSA)
    2023 edition -> Table 7.4 (S. aureus), Table 7.9 (MRSA)
    2022 edition -> Table 6.4 (S. aureus), Table 6.9 (MRSA)

Chapter-specific things that differ from the Gram-negative chapters:

* Caption grammar is different again: "Table 6.4: **Year-wise** susceptibility
  **trends** of S. aureus **from** all samples" -- not "Yearly susceptibility
  trend of ... isolated from ...". A parser keyed to the Enterobacterales
  wording finds nothing at all here.
* Table 6.9 (MRSA) wraps its year header across two grid rows: "Year-2020"
  lands on one row while the other seven years appear as bare digits on the
  next. Handled by the header-merging logic in base.py.
* Entirely different drug classes, as expected for Gram-positives, and
  S. aureus and MRSA do not share a panel -- the MRSA table omits
  cotrimoxazole and linezolid.
* Daptomycin appears in the specimen-wise tables but NOT in either yearly
  trend table, so it is deliberately absent from both panels here.

**MRSA here means susceptibility of MRSA isolates to each drug.** It is not
MRSA prevalence. The frequently quoted "MRSA rose from 33% in 2017 to nearly
53% in 2024" is a prevalence figure -- the share of S. aureus that is
methicillin-resistant -- and comes from a different table entirely. Do not
validate one against the other.
"""

from __future__ import annotations

from .trend_parser import OrganismSpec, parse_report as _parse

S_AUREUS_PANEL = [
    "cefoxitin",
    "oxacillin",
    "vancomycin",
    "teicoplanin",
    "erythromycin",
    "tetracycline",
    "tigecycline",
    "ciprofloxacin",
    "clindamycin",
    "cotrimoxazole",
    "linezolid",
]

MRSA_PANEL = [
    "cefoxitin",
    "oxacillin",
    "vancomycin",
    "teicoplanin",
    "erythromycin",
    "tetracycline",
    "tigecycline",
    "ciprofloxacin",
    "clindamycin",
]

# These tables are captioned "from all samples"; the chapter also carries
# blood / superficial / deep-infection tables that must not be picked up.
_REJECT = (
    r"\bfrom\s+urine\b|\bfrom\s+blood\b|superficial|deep\s+infection|"
    r"pus|exudates|faeces"
)

SPECS = {
    "Staphylococcus aureus": OrganismSpec(
        name="Staphylococcus aureus",
        # Must not swallow the MRSA table, which is a distinct caption.
        pattern=r"\b(?:S\.?\s*aureus|Staphylococcus\s+aureus)\b",
        panel=S_AUREUS_PANEL,
        reject=_REJECT,
    ),
    "MRSA": OrganismSpec(
        name="MRSA",
        pattern=r"\bMRSA\b",
        panel=MRSA_PANEL,
        reject=_REJECT,
    ),
}

ORGANISMS = SPECS


def parse_report(source, organism: str, extracted_date=None):
    if organism not in SPECS:
        raise KeyError(
            "unknown organism {!r}; known: {}".format(organism, sorted(SPECS))
        )
    return _parse(source, SPECS[organism], extracted_date)
