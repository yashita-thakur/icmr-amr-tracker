"""Non-fermenting Gram-negative bacilli (NFGNB) yearly trend tables.

    2024 edition -> Table 3.3 (P. aeruginosa), Table 3.6 (A. baumannii)
    2023 edition -> Table 4.6 (P. aeruginosa), Table 4.3 (A. baumannii)
    2022 edition -> Table 5.3 (P. aeruginosa), Table 5.6 (A. baumannii)

Chapter-specific things that differ from Enterobacterales:

* The 2022 edition captions these "Yearly **susceptible** trend of ...", not
  "Yearly susceptibility trend of ...". Handled by `CAPTION_RE` in base.py.
* The specimen wording is looser and inconsistent: "from all samples",
  "from all samples except faeces", "from all samples (except faeces)".
* The two organisms do NOT share a panel. A. baumannii carries minocycline;
  P. aeruginosa carries gentamicin, tobramycin and ciprofloxacin instead.
  Neither carries ertapenem or cefazolin -- non-fermenters are not tested like
  Enterobacterales.
* **Colistin is not a susceptibility figure here.** Both tables footnote it:
  "*Colistin represents percentage intermediate susceptibility". Those records
  are flagged so the number is never read as ordinary susceptibility.

Do not confuse these with Table 1.12b, which is a yearly *isolation* trend
(how many isolates were found), not a susceptibility trend.
"""

from __future__ import annotations

from .trend_parser import OrganismSpec, parse_report as _parse

COLISTIN_FLAG = "colistin_is_intermediate_susceptibility"

ACINETOBACTER_PANEL = [
    "piperacillin-tazobactam",
    "cefepime",
    "ceftazidime",
    "imipenem",
    "meropenem",
    "colistin",
    "amikacin",
    "minocycline",
    "levofloxacin",
]

PSEUDOMONAS_PANEL = [
    "piperacillin-tazobactam",
    "cefepime",
    "ceftazidime",
    "imipenem",
    "meropenem",
    "colistin",
    "amikacin",
    "gentamicin",
    "tobramycin",
    "ciprofloxacin",
    "levofloxacin",
]

SPECS = {
    "Acinetobacter baumannii": OrganismSpec(
        name="Acinetobacter baumannii",
        pattern=r"\b(?:A\.?\s*baumannii|Acinetobacter\s+baumannii)\b",
        panel=ACINETOBACTER_PANEL,
        flag_rules={"colistin": COLISTIN_FLAG},
    ),
    "Pseudomonas aeruginosa": OrganismSpec(
        name="Pseudomonas aeruginosa",
        pattern=r"\b(?:P\.?\s*aeruginosa|Pseudomonas\s+aeruginosa)\b",
        panel=PSEUDOMONAS_PANEL,
        flag_rules={"colistin": COLISTIN_FLAG},
    ),
}

ORGANISMS = SPECS


def parse_report(source, organism: str, extracted_date=None):
    if organism not in SPECS:
        raise KeyError(
            "unknown organism {!r}; known: {}".format(organism, sorted(SPECS))
        )
    return _parse(source, SPECS[organism], extracted_date)
