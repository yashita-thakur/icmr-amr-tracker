"""V3 -- NCDC NARS-Net specimen-wise resistance tables.

Scope of this module as it stands: the **2019 and 2020** editions, *E. coli* and
*S. aureus*. Those two editions come first because they are the only ones where
the printed numerator is complete and usable, so every cell can be checked
against its own printed percentage. The 2022-2024 editions print no numerator at
all, and a mis-cut column there yields a plausible-looking number with nothing in
the document to contradict it. Proving the geometry where the document can
contradict it comes first.

A third table shape
-------------------
V1's tables are drugs down, years across, one `n / N (pct)` per cell. V2's are
Regional Centres down, drugs across, same cell grammar. NARS-Net is neither:
drugs run down, and across the top sit SPECIMEN GROUPS, each split into three
separate columns -- `Number tested`, `Number Resistant`, `%R`. So `base.py`'s
`parse_measurement` does not apply; there is no fraction in a cell to parse.
What is reused is the machinery that does carry over: ruling-line table
detection to bound the region, and whole-word geometry rather than pdfplumber's
per-cell text.

Column geometry is read from the sub-header row, not guessed. The `%R` and
`Resistant` words give one x-centre per specimen group; the `tested` word
belonging to a group is the last one to its group's left. Taking `tested` only
from the sub-header line also sidesteps the row-label header, which reads
"Antibiotic tested" and would otherwise contribute a fourth `tested` column.

Labels are not on the same line as their values
-----------------------------------------------
In the 2019 edition the antibiotic label sits several points BELOW its own value
row ("Cefoxitin" at y=158 against values at y=152), while in 2020 the two share
a line. Rows are therefore banded on the VALUE words and the label is drawn in
from the band around them, rather than assuming a shared baseline.

Metric direction
----------------
Every value here is **% resistant**. AMRSN publishes **% susceptible**, and
publishes no % intermediate for either of these organisms, so an AMRSN
% resistant cannot be computed and the two networks cannot be joined on a single
shared value. `NarsNetRecord` therefore has no field that means the same thing
as `Record.susceptible_pct`; the separation is structural rather than a
convention to remember.

Reconciliation
--------------
`%R` is printed to whole numbers on most rows and to one decimal on a few, so a
cell reconciles when the printed percentage is within half of its own printed
precision of the numerator over the denominator. Cells outside that carry
`pct_mismatch`, flagged and kept, never corrected.
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import asdict, dataclass, field

import pdfplumber

from .narsnet_antibiotics import normalise_narsnet_antibiotic

# --- schema -----------------------------------------------------------------

# Atomic specimen strata, as the reports stratify them. A composite column is
# never given one of these values; composites join their constituents with "+",
# so `specimen == "blood"` can never accidentally select a pooled column and a
# composite is recognisable without a lookup table.
BLOOD = "blood"
URINE = "urine"
PUS_ASPIRATE = "pus_aspirate"
OSBF = "osbf"
ATOMIC_SPECIMENS = (BLOOD, URINE, PUS_ASPIRATE, OSBF)

# Order composites are written in, so "Blood + PA + OSBF" and "PA + OSBF + Blood"
# would both render as the same value.
_SPECIMEN_ORDER = {BLOOD: 0, URINE: 1, PUS_ASPIRATE: 2, OSBF: 3}

# Numerator provenance. The distinction matters because "not printed" and "zero"
# are different facts about the source, and neither is an extraction failure.
NUMERATOR_PRINTED = "printed"
NUMERATOR_NOT_PRINTED = "not_printed_in_source"
NUMERATOR_CORRUPT = "corrupt_in_source"


@dataclass
class NarsNetRecord:
    """One antibiotic x specimen cell from one NARS-Net edition.

    `year` and `source_report_year` are always equal: a NARS-Net edition reports
    its own reporting period and carries no retrospective multi-year table. Both
    are kept so the row lines up field-for-field with the AMRSN datasets.
    """

    network: str
    organism: str
    antibiotic: str
    specimen: str
    year: int
    tested_n: int | None
    resistant_n: int | None
    resistant_pct: float | None
    numerator_status: str
    reconcilable: bool
    ci_low: float | None
    ci_high: float | None
    source_report_year: int
    source_cover_year: int | None
    source_table: str
    source_url: str
    extracted_date: str
    reported_pct: float | None = None
    computed_pct: float | None = None
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["flags"] = ",".join(self.flags)
        return d


NARSNET_FIELDNAMES = [
    "network",
    "organism",
    "antibiotic",
    "specimen",
    "year",
    "tested_n",
    "resistant_n",
    "resistant_pct",
    "numerator_status",
    "reconcilable",
    "ci_low",
    "ci_high",
    "source_report_year",
    "source_cover_year",
    "source_table",
    "source_url",
    "extracted_date",
    "reported_pct",
    "computed_pct",
    "flags",
]


# --- caption location -------------------------------------------------------

# "Table 4 Resistance profile of Staphylococcus aureus"          (2019)
# "Table 6: Resistance profile of E. coli"                       (2019)
# "Table 5. Resistance profile of Staphylococcus aureus (N= 9,639)"  (2020)
# "Table 8. Specimen wise resistance profile of E. coli (N=17,271 )" (2020)
CAPTION_RE = re.compile(
    r"Table\s*(?P<table>\d+[a-z]?)\s*[:.\-]?\s*"
    r"(?:Specimen[\s\-]*wise\s+)?"
    r"Resistance\s+profile\s+of\s+(?P<rest>.{0,120})",
    re.IGNORECASE | re.DOTALL,
)

# The 2020 edition also carries "Table 6 - Overall resistance profile of
# Staphylococcus aureus isolates to different antimicrobials", a four-row
# antibiotic/%R summary with no counts and no specimen dimension. It must not be
# mistaken for the specimen-wise table.
REJECT_RE = re.compile(r"\boverall\b", re.IGNORECASE)

_TABLE_SETTINGS = {"vertical_strategy": "lines", "horizontal_strategy": "lines"}

_SUB_HEADER_WORDS = {"number", "tested", "resistant", "%r"}


@dataclass
class CaptionHit:
    page_index: int
    table_number: str
    caption: str


def _centre(word) -> float:
    return (word["x0"] + word["x1"]) / 2.0


def find_narsnet_table(pdf, organism_re, reject=None):
    """Locate an organism's specimen-wise table, by caption AND by shape.

    Caption text alone is not enough here. Every edition opens with a List of
    Tables that repeats the captions verbatim, and a caption-only search lands
    there rather than on the table. A page qualifies only if it also carries the
    sub-header a specimen-wise table has -- at least two `%R` columns -- so the
    contents page cannot win.
    """
    for index, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        for m in CAPTION_RE.finditer(text):
            rest = m.group("rest")
            head = text[max(0, m.start() - 40):m.start()]
            if REJECT_RE.search(head) or REJECT_RE.search(rest[:40]):
                continue
            if not organism_re.search(rest):
                continue
            if reject is not None and reject.search(rest):
                continue
            pct_words = [
                w for w in page.extract_words() if w["text"].lower() == "%r"
            ]
            if len(pct_words) < 2:
                continue
            caption = " ".join(m.group(0).split())
            return CaptionHit(index, m.group("table"), caption)
    raise RuntimeError(
        "no specimen-wise resistance table found for {}".format(organism_re.pattern)
    )


# --- specimen headers -------------------------------------------------------

_SPECIMEN_TOKENS = [
    (re.compile(r"^blood$", re.I), BLOOD),
    (re.compile(r"^urine$", re.I), URINE),
    (re.compile(r"^(pa|pus)$", re.I), PUS_ASPIRATE),
    (re.compile(r"^osbf$", re.I), OSBF),
]


def specimen_key(header: str) -> str:
    """Turn a printed specimen header into a canonical specimen value.

    "Blood (N=4,976)"                   -> "blood"
    "PA+OSBF (N=8,314)"                 -> "pus_aspirate+osbf"
    "Blood + Urine + PA + OSBF (N=...)" -> "blood+urine+pus_aspirate+osbf"

    A composite keeps every constituent in its value rather than collapsing to a
    single "pooled" label, because the composites are not the same set across
    editions -- the 2019 E. coli pooled column includes urine and the 2019
    S. aureus one does not. One shared name for both would silently merge two
    different denominators.
    """
    text = re.sub(r"\(.*?\)", " ", header or "")
    parts = [p for p in re.split(r"[+,/&]|\band\b", text) if p.strip()]
    found = []
    for part in parts:
        for word in part.split():
            token = re.sub(r"[^A-Za-z]", "", word)
            for pattern, canonical in _SPECIMEN_TOKENS:
                if pattern.match(token) and canonical not in found:
                    found.append(canonical)
                    break
    if not found:
        raise RuntimeError("could not read a specimen from header {!r}".format(header))
    found.sort(key=lambda s: _SPECIMEN_ORDER[s])
    return "+".join(found)


def is_composite(specimen: str) -> bool:
    return "+" in specimen


# --- table geometry ---------------------------------------------------------


def _line_key(word) -> int:
    return round(word["top"] / 4.0)


def _column_groups(page, region):
    """Read one x-centre triple -- tested, resistant, %R -- per specimen group."""
    x0, top, x1, bottom = region
    words = [
        w
        for w in page.extract_words()
        if x0 - 2 <= _centre(w) <= x1 + 2 and top - 2 <= w["top"] <= bottom + 2
    ]

    by_line: dict[int, list] = {}
    for w in words:
        by_line.setdefault(_line_key(w), []).append(w)

    pct_line = None
    for key in sorted(by_line):
        if len([w for w in by_line[key] if w["text"].lower() == "%r"]) >= 2:
            pct_line = key
            break
    if pct_line is None:
        raise RuntimeError("no %R sub-header row found in the table region")

    res_line = None
    for key in sorted(by_line):
        if key < pct_line:
            continue
        if len([w for w in by_line[key] if w["text"].lower() == "resistant"]) >= 2:
            res_line = key
            break
    if res_line is None:
        raise RuntimeError("no 'Resistant' sub-header row found in the table region")

    pct = sorted(
        [w for w in by_line[pct_line] if w["text"].lower() == "%r"], key=_centre
    )
    # Only the sub-header line's own words, so the row-label header
    # ("Antibiotic tested") cannot contribute a spurious column.
    sub = by_line[res_line]
    res = sorted([w for w in sub if w["text"].lower() == "resistant"], key=_centre)
    tested = sorted([w for w in sub if w["text"].lower() == "tested"], key=_centre)

    if not (len(pct) == len(res) == len(tested)):
        raise RuntimeError(
            "sub-header is not a whole number of specimen groups: "
            "{} %R, {} Resistant, {} tested".format(len(pct), len(res), len(tested))
        )

    groups = []
    for p, r, t in zip(pct, res, tested):
        if not (_centre(t) < _centre(r) < _centre(p)):
            raise RuntimeError(
                "specimen group columns are out of order: tested/resistant/%R at "
                "{:.0f}/{:.0f}/{:.0f}".format(_centre(t), _centre(r), _centre(p))
            )
        groups.append(
            {
                "tested": _centre(t),
                "resistant": _centre(r),
                "pct": _centre(p),
                "left": t["x0"],
                "right": p["x1"],
            }
        )

    header_bottom = max(w["bottom"] for w in by_line[res_line])
    header_words = [
        w
        for w in words
        if _line_key(w) < pct_line and w["text"].lower() not in _SUB_HEADER_WORDS
    ]
    for g in groups:
        owned = [w for w in header_words if g["left"] - 6 <= _centre(w) <= g["right"] + 6]
        owned.sort(key=lambda w: (_line_key(w), w["x0"]))
        g["header"] = " ".join(w["text"] for w in owned)
        g["specimen"] = specimen_key(g["header"])

    return groups, header_bottom


_NUMBER_RE = re.compile(r"^\d[\d,]*(?:\.\d+)?$")


def _int(text: str) -> int:
    return int(text.replace(",", ""))


def _decimals(text: str) -> int:
    return len(text.split(".")[1]) if "." in text else 0


def pct_tolerance(printed: str) -> float:
    """Half the printed precision: 0.5 for a whole number, 0.05 for one decimal.

    Anything inside this is the source's own rounding. Anything outside it is a
    real disagreement between the printed percentage and the printed counts, and
    is flagged rather than smoothed away.
    """
    return 0.5 * (10.0 ** -_decimals(printed)) + 1e-9


def _data_rows(page, region, groups, header_bottom):
    """Band rows on their value words, then draw in each row's label.

    The 2019 tables print an antibiotic label several points below its own value
    row, so a row cannot be assembled from a shared baseline.
    """
    x0, _top, x1, bottom = region
    words = [
        w
        for w in page.extract_words()
        if x0 - 2 <= _centre(w) <= x1 + 2 and header_bottom + 1 < w["top"] <= bottom
    ]

    centres = []
    for g in groups:
        centres.extend([g["tested"], g["resistant"], g["pct"]])
    label_edge = min(centres) - 0.5 * min(
        abs(b - a) for a, b in zip(sorted(centres), sorted(centres)[1:])
    )

    values = [w for w in words if _NUMBER_RE.match(w["text"]) and _centre(w) > label_edge]
    labels = [w for w in words if _centre(w) <= label_edge]

    bands: dict[int, list] = {}
    for w in values:
        bands.setdefault(_line_key(w), []).append(w)
    ordered = sorted(bands)

    rows = []
    for i, key in enumerate(ordered):
        band = bands[key]
        mid = sum((w["top"] + w["bottom"]) / 2.0 for w in band) / len(band)
        lo = (mid + rows[-1]["mid"]) / 2.0 if rows else mid - 1e9
        hi = None
        if i + 1 < len(ordered):
            nxt = bands[ordered[i + 1]]
            nxt_mid = sum((w["top"] + w["bottom"]) / 2.0 for w in nxt) / len(nxt)
            hi = (mid + nxt_mid) / 2.0
        rows.append({"mid": mid, "lo": lo, "hi": hi, "words": band})

    for row in rows:
        hi = row["hi"] if row["hi"] is not None else 1e9
        owned = [
            w for w in labels if row["lo"] < (w["top"] + w["bottom"]) / 2.0 <= hi
        ]
        owned.sort(key=lambda w: (_line_key(w), w["x0"]))
        row["label"] = " ".join(w["text"] for w in owned)

    return rows


def _assign(row_words, groups):
    """Put each value word in its column, by nearest x-centre."""
    columns = []
    for gi, g in enumerate(groups):
        for field_name in ("tested", "resistant", "pct"):
            columns.append((g[field_name], gi, field_name))
    gaps = [b[0] - a[0] for a, b in zip(sorted(columns), sorted(columns)[1:])]
    limit = 0.5 * min(gaps)

    cells: dict = {}
    for w in row_words:
        centre = _centre(w)
        x, gi, field_name = min(columns, key=lambda c: abs(c[0] - centre))
        if abs(x - centre) > limit:
            continue
        cells.setdefault(gi, {})[field_name] = w["text"]
    return cells


# --- organism specs ---------------------------------------------------------


class NarsNetSpec:
    def __init__(self, name, pattern, reject=None):
        self.name = name
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.reject = re.compile(reject, re.IGNORECASE) if reject else None


SPECS = {
    "Escherichia coli": NarsNetSpec(
        name="Escherichia coli",
        # The 2020-2022 editions print "Escherichia Coli" with a capital C.
        pattern=r"\b(?:E\.?\s*coli|Escherichia\s+coli)\b",
    ),
    "Staphylococcus aureus": NarsNetSpec(
        name="Staphylococcus aureus",
        pattern=r"\b(?:S\.?\s*aureus|Staph(?:\.|ylococcus)?\s*aureus)\b",
    ),
}

# Editions this module has been built and checked against. Later editions change
# the column structure -- 2021 prints a numerator that is partly corrupt, and
# 2022-2024 replace it with a 95% CI -- so they are deliberately not claimed here.
EXPECTED_EDITIONS = {
    "Escherichia coli": {2019, 2020},
    "Staphylococcus aureus": {2019, 2020},
}


# --- driver -----------------------------------------------------------------


def parse_narsnet_report(source, spec: NarsNetSpec, extracted_date=None):
    """Extract one organism's specimen-wise resistance table from one edition."""
    extracted_date = extracted_date or _dt.date.today().isoformat()

    if not source.path.exists():
        raise FileNotFoundError(
            "{} not found. Run `python -m src.fetch --network narsnet` first.".format(
                source.path
            )
        )

    records: list[NarsNetRecord] = []
    with pdfplumber.open(source.path) as pdf:
        hit = find_narsnet_table(pdf, spec.pattern, spec.reject)
        page = pdf.pages[hit.page_index]

        tables = page.find_tables(table_settings=_TABLE_SETTINGS)
        if not tables:
            raise RuntimeError(
                "{} {} ({}): pdfplumber found no ruled table on page {}. STOP: do "
                "not fall back to regex over raw text -- the text layer does not "
                "preserve column alignment.".format(
                    source.report_year, hit.table_number, spec.name, page.page_number
                )
            )
        region = max(
            (t.bbox for t in tables),
            key=lambda b: (b[2] - b[0]) * (b[3] - b[1]),
        )

        groups, header_bottom = _column_groups(page, region)
        rows = _data_rows(page, region, groups, header_bottom)

        seen = set()
        for row in rows:
            antibiotic = normalise_narsnet_antibiotic(row["label"])
            if antibiotic is None:
                continue
            cells = _assign(row["words"], groups)
            for gi, g in enumerate(groups):
                cell = cells.get(gi)
                if not cell:
                    # A greyed-out block: the drug is not reported for this
                    # specimen at all. Nothing was printed, so nothing is emitted.
                    continue
                key = (antibiotic, g["specimen"])
                if key in seen:
                    continue
                seen.add(key)
                records.append(
                    _record(source, spec, hit, antibiotic, g, cell, extracted_date)
                )

    if not records:
        raise RuntimeError(
            "{} {} ({}): extracted zero records".format(
                source.report_year, hit.table_number, spec.name
            )
        )
    return records


def _record(source, spec, hit, antibiotic, group, cell, extracted_date):
    flags: list[str] = []

    tested_text = cell.get("tested")
    resistant_text = cell.get("resistant")
    pct_text = cell.get("pct")

    tested_n = _int(tested_text) if tested_text else None
    resistant_n = _int(resistant_text) if resistant_text else None
    reported_pct = float(pct_text) if pct_text else None

    if resistant_text:
        numerator_status = NUMERATOR_PRINTED
    else:
        numerator_status = NUMERATOR_NOT_PRINTED
        flags.append("numerator_not_printed_in_source")

    if pct_text is None:
        flags.append("pct_suppressed_in_source")

    reconcilable = resistant_n is not None and bool(tested_n)
    computed_pct = None
    if reconcilable:
        computed_pct = round(100.0 * resistant_n / tested_n, 2)
        if reported_pct is not None:
            if abs(reported_pct - computed_pct) > pct_tolerance(pct_text):
                flags.append(
                    "pct_mismatch(reported={},computed={})".format(
                        reported_pct, computed_pct
                    )
                )
    if resistant_n is not None and tested_n == 0:
        flags.append("no_isolates_tested")

    return NarsNetRecord(
        network=source.network,
        organism=spec.name,
        antibiotic=antibiotic,
        specimen=group["specimen"],
        year=source.report_year,
        tested_n=tested_n,
        resistant_n=resistant_n,
        # Only ever what the source printed. A percentage is never back-filled
        # from the counts, and a numerator is never back-computed from a
        # percentage -- see the module docstring.
        resistant_pct=reported_pct,
        numerator_status=numerator_status,
        reconcilable=reconcilable,
        ci_low=None,
        ci_high=None,
        source_report_year=source.report_year,
        source_cover_year=source.cover_year,
        source_table="Table {}".format(hit.table_number),
        source_url=source.url,
        extracted_date=extracted_date,
        reported_pct=reported_pct,
        computed_pct=computed_pct,
        flags=flags,
    )
