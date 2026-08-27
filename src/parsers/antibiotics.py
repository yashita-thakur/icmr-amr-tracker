"""Canonical antibiotic names shared by every chapter parser.

Panels differ sharply by organism group -- Enterobacterales, non-fermenters and
staphylococci are not tested against the same drugs, and even the two
non-fermenters differ from each other (A. baumannii carries minocycline;
P. aeruginosa carries gentamicin, tobramycin and ciprofloxacin instead). The
name normalisation, however, is common, so it lives here rather than being
copied per chapter.
"""

from __future__ import annotations

import re

ALIASES: dict[str, str] = {
    # beta-lactam / beta-lactamase inhibitor
    "piperacillintazobactam": "piperacillin-tazobactam",
    "piptazobactam": "piperacillin-tazobactam",
    "piperacillintazobactum": "piperacillin-tazobactam",
    # cephalosporins
    "cefazolin": "cefazolin",
    "cefotaxime": "cefotaxime",
    "ceftazidime": "ceftazidime",
    "ceftriaxone": "ceftriaxone",
    "cefepime": "cefepime",
    "cefoxitin": "cefoxitin",
    # carbapenems
    "ertapenem": "ertapenem",
    "imipenem": "imipenem",
    "meropenem": "meropenem",
    # aminoglycosides
    "amikacin": "amikacin",
    "gentamicin": "gentamicin",
    "tobramycin": "tobramycin",
    # fluoroquinolones
    "ciprofloxacin": "ciprofloxacin",
    "levofloxacin": "levofloxacin",
    # polymyxins
    "colistin": "colistin",
    "polymyxinb": "polymyxin B",
    # tetracyclines / glycylcyclines
    "tetracycline": "tetracycline",
    "minocycline": "minocycline",
    "doxycycline": "doxycycline",
    "tigecycline": "tigecycline",
    # glycopeptides / lipopeptides / oxazolidinones
    "vancomycin": "vancomycin",
    "teicoplanin": "teicoplanin",
    "daptomycin": "daptomycin",
    "linezolid": "linezolid",
    # anti-staphylococcal penicillins
    "oxacillin": "oxacillin",
    "methicillin": "methicillin",
    # macrolides / lincosamides
    "erythromycin": "erythromycin",
    "clindamycin": "clindamycin",
    # folate pathway inhibitors
    "cotrimoxazole": "cotrimoxazole",
    "trimethoprimsulfamethoxazole": "cotrimoxazole",
    "trimethoprim": "cotrimoxazole",
    "sulfamethoxazole": "cotrimoxazole",
    # urinary agents
    "fosfomycin": "fosfomycin",
    "nitrofurantoin": "nitrofurantoin",
}

# Longest first, so "trimethoprimsulfamethoxazole" wins over "trimethoprim" and
# no short alias can capture a label that names a longer drug.
_BY_LENGTH = sorted(ALIASES.items(), key=lambda kv: -len(kv[0]))

_NOISE_RE = re.compile(r"[^a-z]+")


def normalise_antibiotic(label) -> str | None:
    """Map a raw label onto a canonical antibiotic name.

    Labels arrive with wrapping, stray hyphens and footnote markers:
    "Piperacillin- tazobactam", "Piperacillin tazobactam", "Colistin*" and
    "Trimethoprim- sulfamethoxazole" all appear in the reports. Squashing to
    letters only collapses every one of those to a single lookup key.
    """
    if not label:
        return None
    key = _NOISE_RE.sub("", " ".join(str(label).split()).lower())
    if not key:
        return None
    if key in ALIASES:
        return ALIASES[key]
    for alias, canonical in _BY_LENGTH:
        if alias in key:
            return canonical
    return None
