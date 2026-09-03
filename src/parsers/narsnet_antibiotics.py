"""Antibiotic label normalisation for the NCDC NARS-Net reports (V3).

This is a second alias table, consulted before the shared one in
`antibiotics.py`. That module is deliberately NOT edited and nothing is added to
its `ALIASES`, for a specific reason rather than tidiness:
`normalise_antibiotic` ends in a SUBSTRING SCAN over every alias, longest first.
Any short key added to the shared table therefore becomes a candidate substring
for every AMRSN label as well, and could silently change how one of them
resolves. Consulting a NARS-Net table first, and never adding to the shared one,
leaves the AMRSN path unchanged by construction -- a property
`tests/test_narsnet_antibiotics.py` pins rather than assumes.

Canonical names are shared with the AMRSN side wherever the drug is the same
(`cotrimoxazole`, `piperacillin-tazobactam`, `gentamicin`), so the two networks'
rows can be lined up on the `antibiotic` column. Only three canonical names are
new here, for drugs NARS-Net tests and AMRSN does not: `ampicillin`,
`cefuroxime` and `amoxicillin-clavulanate`, spelled in the house style already
used for `piperacillin-tazobactam`.

The printed forms below are the ones recorded in `docs/narsnet_v3_research.md`
(A2, "Naming variants requiring normalisation", plus the per-edition panel
tables). Note that the 2024 report is internally inconsistent -- `TMP/SMX` in
Table 6 but `TMP-SMX` in Table 8, in the same document -- so normalisation is
per cell, never per edition.

Only an EXACT key match is tried here before delegating. Partial labels are not
this function's problem: a wrapped label is reassembled from its rows by the
parser and normalised once, whole, exactly as `trend_parser.py` already does for
the AMRSN tables. A fragment should fail to resolve rather than be guessed at.
"""

from __future__ import annotations

from .antibiotics import _NOISE_RE, normalise_antibiotic

# Keys are labels squashed to letters only, so one key covers every punctuation
# and capitalisation variant of the same printed form. The comment on each line
# is the set of forms actually printed in the reports.
NARSNET_ALIASES: dict[str, str] = {
    # folate pathway inhibitors.
    # "Trimethoprim/Sulfamethoxazole" and "Trimethoprim/sulfamethoxazole"
    # already resolve through the shared table; the abbreviations do not.
    "tmpsmx": "cotrimoxazole",  # TMP/SMX | TMP-SMX | TMP / SMX
    # beta-lactam / beta-lactamase inhibitor combinations.
    # "Piperacillin/ Tazobactam" already resolves through the shared table.
    "piptaz": "piperacillin-tazobactam",  # Pip/Taz | Pip-Taz
    # Amoxicillin-clavulanate is in no AMRSN panel, so both its printed forms
    # are new. Four spellings appear across the series and collapse to two keys.
    "amoxclav": "amoxicillin-clavulanate",  # Amox/Clav | Amox-clav | Amox-Clav
    "amoxicillinclavulanicacid": "amoxicillin-clavulanate",  # Amoxicillin/ Clavulanic acid
    # aminoglycosides. The 2017 edition spells it with a y; corrected from 2018.
    "gentamycin": "gentamicin",  # Gentamycin
    # penicillins. Ampicillin is in every NARS-Net E. coli panel and no AMRSN one.
    "ampicillin": "ampicillin",
    # cephalosporins. Cefuroxime is in the 2021 and 2022 E. coli panels only --
    # the 2023 edition drops it and adds ceftriaxone at the same panel size.
    "cefuroxime": "cefuroxime",
}


def _key(label) -> str:
    """Squash a label to letters only, the same rule the shared table uses.

    Imported rather than re-implemented: two squashing rules that drifted apart
    would map the same printed label to two different keys, which is precisely
    the kind of silent divergence this split is meant to avoid.
    """
    return _NOISE_RE.sub("", " ".join(str(label).split()).lower())


def normalise_narsnet_antibiotic(label) -> str | None:
    """Map a NARS-Net label onto a canonical antibiotic name.

    The NARS-Net table is tried first, by exact key. Everything else -- which is
    most of both panels -- delegates to the shared `normalise_antibiotic`, so a
    drug named identically by both networks resolves through one definition.
    """
    if not label:
        return None
    key = _key(label)
    if not key:
        return None
    if key in NARSNET_ALIASES:
        return NARSNET_ALIASES[key]
    return normalise_antibiotic(label)
