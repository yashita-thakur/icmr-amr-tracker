"""V3 -- NCDC NARS-Net specimen-wise resistance tables.

Scope of this module: the **2019 to 2024** editions, *E. coli* and *S. aureus*.
Those are the editions carrying something a cell can be checked against. The
2017 and 2018 editions print a denominator and a percentage and nothing else,
so a mis-cut column there would yield a plausible-looking number with nothing in
the document to contradict it; they are not claimed.

What the check is changes twice inside the window, because what is printed does:

* **2019-2021** print `Number tested`, `Number Resistant` and `%R`, so each
  cell is checked against its own printed percentage.
* **2022-2024** print `Number Tested`, `(%R)` and a **95% CI**, and no
  numerator at all. `numerator_status` is `not_printed_in_source` on every one
  of those rows and `reconcilable` is false, so the absence of the first check
  is recorded rather than assumed. A numerator is never back-computed as
  denominator x %R: it would be the only invented count in the repository, and
  checking the percentage against it would be circular. The check that applies
  instead is the percentage against its own interval -- see below.

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

Two sources of column geometry, chosen by what the page shows
-------------------------------------------------------------
A column's x-interval is read from the table's own ruled cells across the DATA
rows, and the sub-header words are used only to say which of the three a column
is. The 2019 and 2020 sub-headers are horizontal and sit centred over their
columns, so their own centres would serve; the 2021 sub-headers are rotated a
quarter turn and sit wherever their cell leaves room, far enough off centre in
the narrower columns to fall closer to a neighbour than to their own. The drawn
grid does not move, so the geometry is taken from that instead.

Two artefacts of the grid are handled explicitly. A rule drawn as two strokes
leaves a sliver a few points wide between them, which pdfplumber reports as a
cell of its own; a sliver holds no value word, so it is not a column. A merged
header cell spans the columns beneath it, so an interval containing another is
not a column either. What should survive is one row-label column plus a whole
number of three-column specimen groups.

Where it does not, the grid did not divide the groups. The 2023 and 2024 tables
rule the group boundaries and nothing inside them, so the sub-columns are read
from the sub-header words instead -- and only when every one of them is
horizontal, which is exactly the condition under which a word's position says
where its column is. A table whose grid does not divide it AND whose sub-header
is rotated stops the parser; both sources would be guesses, and guessing past
that is how a column gets mis-cut without anyone noticing. Which source applied
is decided per table by what the page shows, never by edition year.

Rotated sub-headers read backwards
----------------------------------
In the 2021 edition every sub-header word is set rotated a quarter turn, and
pdfplumber, which orders characters top-down, hands them back reversed --
`Number` arrives as `rebmuN`. `_text` puts a non-upright word back into reading
order. That edition also renames the percentage column, from `%R` to
`Resistance (%)` in the S. aureus table and `Resistance %` in the E. coli one,
so the column is recognised by its percent sign rather than by a fixed word.

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

Reconciliation, 2019-2021
-------------------------
`%R` is printed to whole numbers on most rows and to one decimal on a few, so a
cell reconciles when the printed percentage is within half of its own printed
precision of the numerator over the denominator. Cells outside that carry
`pct_mismatch`, flagged and kept, never corrected.

The percentage against its own interval, 2022-2024
--------------------------------------------------
Those editions print no numerator, so the check above has nothing to run on. A
percentage and a 95% confidence interval are two printed statements about one
quantity, though, and can disagree without a third figure: a point estimate
outside its own interval carries `ci_excludes_point_estimate`. Bounds are used
exactly as printed. Where the upper is printed below the lower the interval is
empty as printed and also carries `ci_bounds_inverted`, because "outside its
interval" understates an interval whose ends are the wrong way round, and
putting them back in order would be a repair.

`summarise_ci_checks` in `narsnet_validate.py` reports how far outside the
percentage falls and whether that distance is within half the precision the
percentage is printed to. The distinction is the point: a percentage printed to
whole numbers beside an interval printed to one decimal can fall a tenth outside
an interval that in fact contains it, which is a difference between how two
columns are rounded rather than a disagreement about the figure.

A numerator that is printed but is not the cell's numerator
------------------------------------------------------------
The 2021 *E. coli* table needs a second, coarser distinction. Its Blood
`Number Resistant` sub-column, and two of its Urine cells, print figures that
are not those cells' numerators; `CORRUPT_NUMERATORS` records what the page
shows. `numerator_status` therefore has a third value, `corrupt_in_source`,
beside `printed` and `not_printed_in_source`, rather than a flag layered on top
of `printed`. Consumers switch on that field to decide whether they may use
`resistant_n`, and with a two-value field plus a flag, a consumer that did not
know to check the flag would read an unusable number as a usable one -- the
same failure the `not_printed_in_source` value exists to prevent. `reconcilable`
is false for those cells: it records whether the printed number can be trusted
as this cell's numerator, not merely whether one was printed.

That is a different statement from `pct_mismatch`, and the two are deliberately
kept apart. A `pct_mismatch` cell prints its own numerator and that numerator
disagrees with the percentage beside it; both are carried and both are flagged.
A corrupt cell prints a figure that is not its numerator, so there is nothing
for the percentage to disagree with. Which cells those are is declared from a
hand-read of the page rather than inferred from the size of the disagreement: a
threshold rule would also re-classify the 2020 *S. aureus* doxycycline Blood
cell, which is a separate finding already recorded a separate way.
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

# Numerator provenance. The distinction matters because "not printed", "zero"
# and "a number that is not this cell's numerator" are three different facts
# about the source, and none of them is an extraction failure.
NUMERATOR_PRINTED = "printed"
NUMERATOR_NOT_PRINTED = "not_printed_in_source"
NUMERATOR_CORRUPT = "corrupt_in_source"


@dataclass(frozen=True)
class CorruptNumerators:
    """A block of cells whose printed `Number Resistant` is not their numerator.

    Declared from a hand-read of the printed page rather than inferred at run
    time. A rule that marked a cell corrupt whenever its counts and its
    percentage disagreed by more than some amount would also catch the 2019 and
    2020 cells that carry `pct_mismatch`, and those are a different finding:
    there the numerator is the cell's own figure and disagrees with the
    percentage beside it, and both are kept and flagged.

    `antibiotics` is None where a whole sub-column is declared. The unit of a
    printing defect can be the sub-column rather than the cell, and where it is,
    a cell inside it that does happen to agree with its own printed percentage
    is not exempted: which values in a displaced column have come to rest on
    their own row is not something the printed table lets a reader establish.
    Those agreements are counted in the extraction report rather than acted on,
    so the judgement stays visible and can be revisited.
    """

    year: int
    organism: str
    specimen: str
    antibiotics: frozenset | None
    note: str


CORRUPT_NUMERATORS: tuple = (
    CorruptNumerators(
        year=2021,
        organism="Escherichia coli",
        specimen=BLOOD,
        antibiotics=None,
        note=(
            "2021 Table 6, the whole Blood `Number Resistant` sub-column. "
            "Eleven of its thirteen printed figures do not follow from the "
            "denominator and the percentage printed beside them, and meropenem "
            "prints 981 resistant of 854 tested, which no count of one set of "
            "isolates can produce. The `Number Tested` and percentage columns "
            "are sound, and the Pus Aspirate and OSBF numerators in the same "
            "table reconcile throughout, so what did not survive printing is "
            "this one sub-column."
        ),
    ),
    CorruptNumerators(
        year=2021,
        organism="Escherichia coli",
        specimen=URINE,
        antibiotics=frozenset({"piperacillin-tazobactam", "cotrimoxazole"}),
        note=(
            "2021 Table 6, two Urine cells. Piperacillin/tazobactam prints "
            "2,937 resistant of 2,937 tested and trimethoprim/sulfamethoxazole "
            "prints 8,918 of 8,918, each beside a printed percentage -- 29 and "
            "59 -- that is not 100. The numerator repeats the denominator "
            "instead of recording a count. Every other Urine numerator in the "
            "table reconciles."
        ),
    ),
)


def find_corrupt_numerators(year, organism, specimen, antibiotic):
    """The declaration covering one cell, or None if none covers it."""
    for entry in CORRUPT_NUMERATORS:
        if (entry.year, entry.organism, entry.specimen) != (year, organism, specimen):
            continue
        if entry.antibiotics is None or antibiotic in entry.antibiotics:
            return entry
    return None


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
# "Table 4: Resistance profile observed in Staphylococcus aureus"    (2021)
# "Table 6: Resistance profile of Escherichia coli"                  (2021)
# The 2021 edition names the organism two ways in the same document: its
# S. aureus caption reads "observed in", its E. coli caption "of".
CAPTION_RE = re.compile(
    r"Table\s*(?P<table>\d+[a-z]?)\s*[:.\-]?\s*"
    r"(?:Specimen[\s\-]*wise\s+)?"
    r"Resistance\s+profile\s+(?:of|observed\s+in)\s+(?P<rest>.{0,120})",
    re.IGNORECASE | re.DOTALL,
)

# The 2020 edition also carries "Table 6 - Overall resistance profile of
# Staphylococcus aureus isolates to different antimicrobials", a four-row
# antibiotic/%R summary with no counts and no specimen dimension. It must not be
# mistaken for the specimen-wise table.
REJECT_RE = re.compile(r"\boverall\b", re.IGNORECASE)

_TABLE_SETTINGS = {"vertical_strategy": "lines", "horizontal_strategy": "lines"}

# The sub-header word that names each column of a specimen group. Brackets are
# stripped before the lookup, because the percentage column is bracketed in some
# editions and not others -- and in the 2022 E. coli table it is printed
# "(% R)", which arrives as the two words "(%" and "R)".
#
# "resistant" is checked before the percent sign because no column carries both,
# and the numerator column is the one whose misreading would be silent.
# "Resistance", the 2021 name of the percentage column, is deliberately absent:
# it is a prose word, and the percent sign beside it identifies the column
# without it.
_ROLE_TOKENS = {
    "tested": "tested",
    "resistant": "resistant",   # 2019-2021
    "%r": "pct",                # 2019, 2020, 2022-2024
    "%": "pct",                 # 2021
    "95%": "ci",                # 2022-2024
    "ci": "ci",
}
_PCT_TOKENS = {token for token, role in _ROLE_TOKENS.items() if role == "pct"}

# The two column layouts the series uses. Both are three columns per specimen
# group, but they are not the same three: the numerator is replaced by a 95%
# confidence interval from the 2022 edition on. A table must be one shape
# throughout -- no edition mixes them, and a table that appeared to would mean
# the columns had been read wrongly.
COUNT_SHAPE = ("tested", "resistant", "pct")   # 2019-2021
CI_SHAPE = ("tested", "pct", "ci")             # 2022-2024
_GROUP_SHAPES = (COUNT_SHAPE, CI_SHAPE)

# Every word that belongs to the sub-header rather than to a specimen heading,
# so that reassembling "Blood (N=1806)" cannot pick up part of the sub-header.
_SUB_HEADER_WORDS = {"number", "resistance", "r"} | set(_ROLE_TOKENS)


def _text(word) -> str:
    """One word, in reading order.

    pdfplumber orders characters top-down, which reverses a word set rotated a
    quarter turn -- every sub-header word in the 2021 edition, where `Number`
    comes back as `rebmuN`.
    """
    return word["text"][::-1] if not word.get("upright", True) else word["text"]


def _role_key(word) -> str:
    """A sub-header word reduced to the token the role table is keyed by."""
    return _text(word).lower().replace("(", "").replace(")", "")


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
                w for w in page.extract_words()
                if _role_key(w) in _PCT_TOKENS
            ]
            if len(pct_words) < 2:
                continue
            caption = " ".join(m.group(0).split())
            return CaptionHit(index, m.group("table"), caption)
    raise RuntimeError(
        "no specimen-wise resistance table found for {}".format(organism_re.pattern)
    )


# --- specimen headers -------------------------------------------------------

# The 2019 and 2020 headings abbreviate; the 2021 headings spell the same two
# strata out ("Pus Aspirate", "Other Sterile Body Fluids"). A spelled-out
# heading is matched as a phrase and removed before the single-word pass, so
# that its separate words cannot be read as separate specimens.
_SPECIMEN_PHRASES = [
    (re.compile(r"other\s+sterile\s+body\s+fluids?", re.I), OSBF),
    (re.compile(r"pus\s+aspirates?", re.I), PUS_ASPIRATE),
]

_SPECIMEN_TOKENS = [
    (re.compile(r"^blood$", re.I), BLOOD),
    (re.compile(r"^urine$", re.I), URINE),
    (re.compile(r"^(pa|pus)$", re.I), PUS_ASPIRATE),
    (re.compile(r"^osbf$", re.I), OSBF),
]


def specimen_key(header: str) -> str:
    """Turn a printed specimen header into a canonical specimen value.

    "Blood (N=4,976)"                    -> "blood"
    "PA+OSBF (N=8,314)"                  -> "pus_aspirate+osbf"
    "Blood + Urine + PA + OSBF (N=...)"  -> "blood+urine+pus_aspirate+osbf"
    "Pus Aspirate (N=6434)"              -> "pus_aspirate"
    "Other Sterile Body Fluids (N=630)"  -> "osbf"

    A composite keeps every constituent in its value rather than collapsing to a
    single "pooled" label, because the composites are not the same set across
    editions -- the 2019 E. coli pooled column includes urine and the 2019
    S. aureus one does not. One shared name for both would silently merge two
    different denominators.
    """
    text = re.sub(r"\(.*?\)", " ", header or "")
    found = []
    for pattern, canonical in _SPECIMEN_PHRASES:
        if pattern.search(text) and canonical not in found:
            found.append(canonical)
        text = pattern.sub(" ", text)
    parts = [p for p in re.split(r"[+,/&]|\band\b", text) if p.strip()]
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


def _content_columns(table, words, header_bottom):
    """The x-interval of every column of the table's data area, left to right.

    Read from the table's own ruled cells across the data rows. Two kinds of
    interval are not columns and are dropped: a sliver left between the two
    strokes of a single thick rule, which holds no value word; and a merged
    header cell, which contains the columns beneath it.
    """
    body = [w for w in words if w["top"] > header_bottom + 1]
    intervals = sorted(
        {
            (round(cell[0], 2), round(cell[2], 2))
            for cell in table.cells
            if cell and cell[1] >= header_bottom - 1
        }
    )
    held = [
        iv for iv in intervals if any(iv[0] <= _centre(w) <= iv[1] for w in body)
    ]
    return [
        a
        for a in held
        if not any(b != a and a[0] <= b[0] and b[1] <= a[1] for b in held)
    ]


def _word_columns(role_words, label_edge, right_edge):
    """Sub-column intervals read from the sub-header words themselves.

    Used only where the ruled grid does not divide a specimen group into its
    three columns -- the 2023 and 2024 tables rule the group boundaries and
    nothing inside them. Consecutive sub-header words naming the same column are
    one run ("95%" and "CI" are one column, not two), and a boundary sits midway
    between one run's right edge and the next run's left edge.

    This is only safe because those editions set the sub-header horizontally
    above its own column. `_column_groups` refuses to use it on a rotated
    sub-header, which is the case where a word's position says nothing about
    where its column is.
    """
    words = sorted(
        (w for w in role_words if _centre(w) > label_edge), key=_centre
    )
    runs: list[dict] = []
    for w in words:
        role = _ROLE_TOKENS[_role_key(w)]
        if runs and runs[-1]["role"] == role:
            runs[-1]["x1"] = max(runs[-1]["x1"], w["x1"])
        else:
            runs.append({"role": role, "x0": w["x0"], "x1": w["x1"]})

    columns, roles = [], []
    for i, run in enumerate(runs):
        left = label_edge if i == 0 else (runs[i - 1]["x1"] + run["x0"]) / 2.0
        right = (
            right_edge
            if i == len(runs) - 1
            else (run["x1"] + runs[i + 1]["x0"]) / 2.0
        )
        columns.append((left, right))
        roles.append(run["role"])
    return columns, roles


def _roles_of(columns, role_words):
    """Name each column from the sub-header words standing over it."""
    roles = []
    for iv in columns:
        named = {
            _ROLE_TOKENS[_role_key(w)]
            for w in role_words
            if iv[0] <= _centre(w) <= iv[1]
        }
        roles.append(
            "resistant"
            if "resistant" in named
            else "ci"
            if "ci" in named
            else "pct"
            if "pct" in named
            else "tested"
            if "tested" in named
            else None
        )
    return roles


def _scan_groups(columns, roles):
    """Consecutive column triples matching one of the two printed layouts.

    The scan steps over anything that does not begin a triple, which is how the
    row-label column is skipped: its heading reads "Antibiotic tested" in every
    edition and would otherwise name it a tested column. The caller checks that
    nothing else was stepped over.
    """
    groups, index = [], 0
    while index + 2 < len(columns) + 1:
        window = tuple(roles[index : index + 3])
        if len(window) == 3 and window in _GROUP_SHAPES:
            groups.append(
                {
                    "shape": window,
                    window[0]: columns[index],
                    window[1]: columns[index + 1],
                    window[2]: columns[index + 2],
                    "left": columns[index][0],
                    "right": columns[index + 2][1],
                }
            )
            index += 3
        else:
            index += 1
    return groups


def _column_groups(page, table):
    """Read one x-interval triple per specimen group, and say which is which.

    Two sources of geometry, in that order:

    * the table's own ruled cells, where the grid divides each group into its
      three columns (2019-2022);
    * the sub-header words, where it does not (2023, 2024), and only when they
      are horizontal.

    Which one applied is decided by whether the ruled columns come out as one
    row-label column plus a whole number of groups, not by edition year, so an
    edition whose ruling changes is handled by what the page shows.
    """
    x0, top, x1, bottom = table.bbox
    words = [
        w
        for w in page.extract_words()
        if x0 - 2 <= _centre(w) <= x1 + 2 and top - 2 <= w["top"] <= bottom + 2
    ]

    role_words = [w for w in words if _role_key(w) in _ROLE_TOKENS]
    if not role_words:
        raise RuntimeError("no sub-header row found in the table region")
    header_bottom = max(w["bottom"] for w in role_words)

    ruled = _content_columns(table, words, header_bottom)
    if not ruled:
        raise RuntimeError("the ruled table has no data columns")
    groups = _scan_groups(ruled, _roles_of(ruled, role_words))
    source = "ruled grid"

    # One row-label column plus a whole number of three-column groups is what a
    # specimen-wise table is. Anything left over means the grid did not divide
    # the groups, not that the table is malformed.
    if not groups or len(groups) * 3 != len(ruled) - 1:
        if not all(w.get("upright", True) for w in role_words):
            raise RuntimeError(
                "the ruled grid does not divide this table into specimen "
                "groups and its sub-header is rotated, so neither source of "
                "column geometry can be trusted: {} ruled column(s), {} "
                "group(s)".format(len(ruled), len(groups))
            )
        columns, roles = _word_columns(role_words, ruled[0][1], x1)
        groups = _scan_groups(columns, roles)
        source = "sub-header words"
        if not groups or len(groups) * 3 != len(columns):
            raise RuntimeError(
                "sub-header does not read as a whole number of specimen "
                "groups: {} column(s), {} group(s), roles {}".format(
                    len(columns), len(groups), roles
                )
            )

    shapes = {g["shape"] for g in groups}
    if len(shapes) != 1:
        raise RuntimeError(
            "table mixes column layouts, which no edition does: {}".format(shapes)
        )

    for g in groups:
        own = [w for w in role_words if g["left"] <= _centre(w) <= g["right"]]
        ceiling = min(w["top"] for w in own)
        owned = [
            w
            for w in words
            if g["left"] <= _centre(w) <= g["right"]
            and w["bottom"] <= ceiling
            and _role_key(w) not in _SUB_HEADER_WORDS
        ]
        owned.sort(key=lambda w: (_line_key(w), w["x0"]))
        g["header"] = " ".join(_text(w) for w in owned)
        g["specimen"] = specimen_key(g["header"])
        g["geometry"] = source

    return groups, header_bottom


_NUMBER_RE = re.compile(r"^\d[\d,]*(?:\.\d+)?$")

# A printed value in any edition: a count, a percentage that may be bracketed,
# or a confidence interval or one half of one. The 2022-2024 tables print some
# intervals with a space after the dash ("31.2- 38.2"), which arrives as two
# words, so a bare "31.2-" has to count as a value or half the interval would be
# dropped. "x", which those editions print where a drug is not tested for a
# specimen, matches nothing here and is not a value.
_VALUE_RE = re.compile(r"^\(?\d[\d,.\-]*\)?$")

# "57.9-60.4", "0-0.1", "34.5-43". Reassembled from the words of one cell.
_CI_RE = re.compile(r"^(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)$")


def _int(text: str) -> int:
    return int(text.replace(",", ""))


def _pct(text: str) -> float:
    """A printed percentage. Bracketed in some editions, bare in others."""
    return float(text.strip("()"))


def _decimals(text: str) -> int:
    return len(text.split(".")[1]) if "." in text else 0


def pct_tolerance(printed: str) -> float:
    """Half the printed precision: 0.5 for a whole number, 0.05 for one decimal.

    Anything inside this is the source's own rounding. Anything outside it is a
    real disagreement between the printed percentage and the printed counts, and
    is flagged rather than smoothed away.
    """
    return 0.5 * (10.0 ** -_decimals(printed)) + 1e-9


def _data_rows(page, table, groups, header_bottom):
    """Band rows on their value words, then draw in each row's label.

    The 2019 tables print an antibiotic label several points below its own value
    row, so a row cannot be assembled from a shared baseline.
    """
    x0, _top, x1, bottom = table.bbox
    words = [
        w
        for w in page.extract_words()
        if x0 - 2 <= _centre(w) <= x1 + 2 and header_bottom + 1 < w["top"] <= bottom
    ]

    # The row-label column is everything left of the first column of the first
    # specimen group, which the ruled grid puts an exact edge on.
    label_edge = min(g["tested"][0] for g in groups)

    values = [
        w for w in words if _VALUE_RE.match(_text(w)) and _centre(w) > label_edge
    ]
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
        row["label"] = " ".join(_text(w) for w in owned)

    return rows


def _assign(row_words, groups):
    """Put each value word in its column, by the interval it sits in.

    A word whose centre falls in no column is dropped rather than attached to
    the nearest one. A column collects every word that lands in it, in printed
    order, because a confidence interval printed with a space after its dash is
    two words of one cell; they are rejoined by the caller.
    """
    columns = []
    for gi, g in enumerate(groups):
        for field_name in g["shape"]:
            columns.append((g[field_name], gi, field_name))

    cells: dict = {}
    for w in sorted(row_words, key=_centre):
        centre = _centre(w)
        for (low, high), gi, field_name in columns:
            if low <= centre <= high:
                cells.setdefault(gi, {}).setdefault(field_name, []).append(_text(w))
                break
    return {gi: {k: "".join(v) for k, v in fields.items()} for gi, fields in cells.items()}


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

# Editions this module has been built and checked against: all eight reporting
# periods NARS-Net has published for these two organisms, less 2017 and 2018,
# which print no numerator and no interval and so support neither internal
# check.
EXPECTED_EDITIONS = {
    "Escherichia coli": {2019, 2020, 2021, 2022, 2023, 2024},
    "Staphylococcus aureus": {2019, 2020, 2021, 2022, 2023, 2024},
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
        table = max(
            tables,
            key=lambda t: (t.bbox[2] - t.bbox[0]) * (t.bbox[3] - t.bbox[1]),
        )

        groups, header_bottom = _column_groups(page, table)
        rows = _data_rows(page, table, groups, header_bottom)

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
    ci_text = cell.get("ci")

    tested_n = _int(tested_text) if tested_text else None
    resistant_n = _int(resistant_text) if resistant_text else None
    reported_pct = _pct(pct_text) if pct_text else None

    ci_low = ci_high = None
    if ci_text:
        m = _CI_RE.match(ci_text)
        if m is None:
            raise RuntimeError(
                "{} {} / {}: 95% CI cell does not read as an interval: "
                "{!r}".format(source.report_year, antibiotic, group["specimen"], ci_text)
            )
        ci_low, ci_high = float(m.group(1)), float(m.group(2))

    corrupt = (
        find_corrupt_numerators(
            source.report_year, spec.name, group["specimen"], antibiotic
        )
        if resistant_text
        else None
    )

    if not resistant_text:
        numerator_status = NUMERATOR_NOT_PRINTED
        flags.append("numerator_not_printed_in_source")
    elif corrupt is not None:
        numerator_status = NUMERATOR_CORRUPT
        flags.append("numerator_corrupt_in_source")
    else:
        numerator_status = NUMERATOR_PRINTED

    if pct_text is None:
        flags.append("pct_suppressed_in_source")

    # The one internal check the 2022-2024 tables can support. With no numerator
    # there is nothing to reconcile a percentage against, but a percentage and
    # its own interval are two printed statements about the same quantity, and a
    # point estimate outside its own interval is a disagreement between them
    # that needs no third figure to see. Bounds are used exactly as printed:
    # where the upper is below the lower the interval is empty as printed, and
    # putting them back in order would be a repair.
    if ci_low is not None and ci_high is not None:
        if ci_high < ci_low:
            flags.append(
                "ci_bounds_inverted(low={},high={})".format(ci_low, ci_high)
            )
        if reported_pct is not None and not ci_low <= reported_pct <= ci_high:
            flags.append(
                "ci_excludes_point_estimate(pct={},ci={}-{})".format(
                    reported_pct, ci_low, ci_high
                )
            )

    # Whether the printed numerator can be trusted as this cell's numerator, not
    # merely whether one was printed. A corrupt cell prints a number and is not
    # reconcilable, and no percentage is computed from it -- computing one would
    # put a figure derived from an unusable count beside the sound printed
    # percentage, where the next reader would have to know which was which.
    reconcilable = numerator_status == NUMERATOR_PRINTED and bool(tested_n)
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
        ci_low=ci_low,
        ci_high=ci_high,
        source_report_year=source.report_year,
        source_cover_year=source.cover_year,
        source_table="Table {}".format(hit.table_number),
        source_url=source.url,
        extracted_date=extracted_date,
        reported_pct=reported_pct,
        computed_pct=computed_pct,
        flags=flags,
    )
