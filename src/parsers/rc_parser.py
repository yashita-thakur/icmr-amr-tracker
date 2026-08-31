"""Regional Centre (RC) breakdown parser -- V2.

Alongside the national yearly-trend tables that V1 extracts, the AMRSN reports
carry a set of *RC-wise* antimicrobial-susceptibility (AMS) tables: one column
per antibiotic, one row per Regional Centre, for the report's own year only.
These are single-year cross-sections, NOT 8-year retrospective trends -- see the
README section "Regional Centre tables are a single-year cross-section" for why
that matters for cross-edition comparison.

Only three of V1's six priority organisms have an RC-wise AMS table for the
non-urine population ("all samples except faeces and urine" / "total except
faeces & urine"):

    Escherichia coli       2023 ed. Table 3.10 · 2024 ed. Table 2.10   (no 2022)
    Klebsiella pneumoniae  2023 ed. Table 3.11 · 2024 ed. Table 2.11   (no 2022)
    Staphylococcus aureus  2022 ed. Table 6.3  · 2023 ed. Table 7.3
                                               · 2024 ed. Table 6.3

A. baumannii, P. aeruginosa and MRSA have no RC-wise AMS table in any edition.
The 2022 edition breaks E. coli / K. pneumoniae down by RC only for *urine*
isolates, which is out of scope here exactly as it is for V1.

The hardening in `base.py` is reused verbatim where it applies: tables are
located by CAPTION MEANING (never table number), cell contents are assembled
from whole WORDS positioned by centre point so no digit can be clipped, and the
printed percentage is checked against n/N. What differs is only the axis --
columns are antibiotics here, not years, and rows are Regional Centres -- so the
column/row geometry is derived here rather than in `base.py`.

RC labels (`RC1`..`RC21`) are DE-IDENTIFIED in the reports; the
code-to-institution mapping is not part of the published tables. They are
therefore edition-scoped: `RC5` in the 2023 edition is not necessarily `RC5` in
the 2024 edition. Comparing an RC across editions is only safe once
`build_rc_dataset` has confirmed the RC panel did not change between them (the
`rc_panel_changed` flag).
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import asdict, dataclass, field

import pdfplumber

from .antibiotics import normalise_antibiotic
from .base import _join_cell_words, _page_text, parse_measurement

# --- schema (V1 schema + regional_centre) ---------------------------------


@dataclass
class RCRecord:
    organism: str
    regional_centre: str
    antibiotic: str
    year: int
    susceptible_n: int | None
    tested_n: int | None
    susceptible_pct: float | None
    source_report_year: int
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


RC_FIELDNAMES = [
    "organism",
    "regional_centre",
    "antibiotic",
    "year",
    "susceptible_n",
    "tested_n",
    "susceptible_pct",
    "source_report_year",
    "source_table",
    "source_url",
    "extracted_date",
    "reported_pct",
    "computed_pct",
    "flags",
]


# --- caption location ----------------------------------------------------

# The RC-wise caption grammar differs by edition, in two orderings:
#
#   2024 ed.:  "Table 2.10: RC-wise Antimicrobial Susceptibility (AMS)
#               percentages of Escherichia coli from total samples
#               (except faeces & urine)"
#              "Table 2.11: RC-wise AMS percentages of K. pneumoniae from
#               total samples (except faeces & urine)"
#   2022/2023: "Table 3.10: Antimicrobial Susceptibilities (AMS) Percentage
#               RC wise of Escherichia coli from Total (Except Faeces & Urine)"
#              "Table 6.3: Antimicrobial Susceptibility (AMS) Percentage RC wise
#               of Staphylococcus aureus from all samples except faeces and
#               urine"
#
# Both orderings carry, on the one caption line, the tokens "RC wise" / "RC-wise"
# and "(AMS)". That pair is what distinguishes these from (a) the national
# yearly-trend captions, which carry neither, (b) the "Regional centre wise
# distribution" isolate-count tables (Table 1.6 etc.), which carry no "AMS", and
# (c) the 2022 urine-only "... overall and RC wise" table, which carries no
# "AMS" and is rejected by the specimen check besides.
_DASH = r"\s\-‐-―"
RC_CAPTION_RE = re.compile(
    r"Table\s*(?P<table>\d+\.\d+[a-z]?)\s*[:.]?\s*"
    r"(?P<rest>"
    r"(?=[^\n]*\bRC[" + _DASH + r"]*wise\b)"
    r"(?=[^\n]*\bAMS\b)"
    r"[^\n]{0,200})",
    re.IGNORECASE,
)


@dataclass
class RCCaptionHit:
    page_index: int
    table_number: str
    caption: str


def find_rc_caption(
    pdf,
    organism_pattern: re.Pattern,
    specimen_pattern: re.Pattern,
    reject_pattern: re.Pattern | None = None,
    cache_key=None,
) -> RCCaptionHit:
    """Find the page carrying the target organism's RC-wise AMS table caption.

    Mirrors `base.find_caption`: matches on caption semantics, reads the table
    number back out of whatever it finds.
    """
    near_misses: list[str] = []
    for i, page in enumerate(pdf.pages):
        text = _page_text(cache_key, i, page)
        # Cheap pre-filter. Must stay in step with RC_CAPTION_RE: every match
        # carries "wise" and "ams" on the caption line, so a page with neither
        # cannot contain one. (CHANGELOG V1.1: a stale pre-filter once skipped a
        # whole chapter whose captions the regex would have matched.)
        low = text.lower()
        if "wise" not in low or "ams" not in low:
            continue
        for m in RC_CAPTION_RE.finditer(text):
            rest = " ".join(m.group("rest").split())
            if not organism_pattern.search(rest):
                continue
            label = "p{} Table {}: {}".format(i + 1, m.group("table"), rest[:90])
            if reject_pattern is not None and reject_pattern.search(rest):
                near_misses.append(label)
                continue
            if not specimen_pattern.search(rest):
                near_misses.append(label)
                continue
            return RCCaptionHit(
                page_index=i,
                table_number="Table " + m.group("table"),
                caption=rest,
            )

    detail = "\n  ".join(near_misses) if near_misses else "(no near misses)"
    raise LookupError(
        "No RC-wise AMS caption for organism={!r} specimen={!r}.\n"
        "Near misses:\n  {}".format(
            organism_pattern.pattern, specimen_pattern.pattern, detail
        )
    )


# --- table geometry ----------------------------------------------------------

RC_LABEL_RE = re.compile(r"^RC[\s\-]*0*(\d{1,3})$", re.IGNORECASE)
TOTAL_LABEL_RE = re.compile(r"^total$", re.IGNORECASE)

# Outer edges of the first/last antibiotic column have no neighbour to split the
# gap with, so widen them by this many points.
OUTER_PAD = 12.0
# Fraction of parsed cells whose printed % must reconcile with n/N for the grid
# to be trusted. Below this the column boundaries are wrong and we raise rather
# than emit plausible-looking mis-paired numbers (base.py, spec section 4.2).
MIN_CONSISTENT = 0.80

# The unit row printed under every column heading ("n(%)" in 2022/2023,
# "(S%)" in 2024). Skipped when naming a column. Deliberately narrow: a bare
# "n" is the tail of "Teicoplanin" wrapped onto its own line, not noise.
_UNIT_ROW_RE = re.compile(r"^(?:n\s*\(\s*%?\s*\)|\(\s*s?\s*%\s*\)|\(%\))$", re.IGNORECASE)


def _rc_canon(text: str):
    m = RC_LABEL_RE.match(text.strip())
    return "RC{}".format(int(m.group(1))) if m else None


@dataclass
class RCColumn:
    left: float
    right: float
    antibiotic: str


def _data_column_centres(words, label_right, data_top):
    """Antibiotic-column centre x-positions, taken from the DATA cells.

    The header of these tables is unreliable for geometry -- drug names wrap
    across two to four lines and the corner "RC / Antibiotics" label splits
    into ruled slivers. The data grid, by contrast, is clean and regular. Every
    data cell is an "n / N" group, so the x-centre of each word carrying a "/"
    is a sample of its column's centre; clustering those samples yields one
    centre per antibiotic column. This inverts `base.py`, which reads column x
    from the header because there the header is the clean part.
    """
    xs = sorted(
        (w["x0"] + w["x1"]) / 2.0
        for w in words
        if "/" in w["text"] and w["top"] >= data_top - 2.0 and (w["x0"] + w["x1"]) / 2.0 > label_right
    )
    if len(xs) < 20:
        raise RuntimeError(
            "RC table: only {} '/' tokens right of the label column; cannot "
            "resolve the data columns.".format(len(xs))
        )
    clusters: list[list] = [[xs[0]]]
    for x in xs[1:]:
        if x - clusters[-1][-1] > 22.0:
            clusters.append([])
        clusters[-1].append(x)
    # A real column contributes one "/" per RC row (~15-21); drop stragglers.
    centres = [sum(cl) / len(cl) for cl in clusters if len(cl) >= 5]
    if len(centres) < 9:
        raise RuntimeError(
            "RC table: resolved only {} antibiotic columns from the data grid "
            "(spec section 4.2 -- not falling back to text).".format(len(centres))
        )
    return centres


def _name_columns(header_words, centres):
    """Name each antibiotic column from the nearest header word(s).

    Each header word is assigned to the single column whose centre is closest,
    then that column's words are joined and normalised. Raises if a column does
    not resolve, or if two columns resolve to the same drug -- an unreadable
    header means the geometry is not to be trusted (base.py, spec section 4.2).
    """
    buckets: list[list] = [[] for _ in centres]
    pitch = (
        min(centres[i + 1] - centres[i] for i in range(len(centres) - 1))
        if len(centres) > 1
        else 60.0
    )
    for w in header_words:
        if _UNIT_ROW_RE.match(w["text"]):
            continue
        cx = (w["x0"] + w["x1"]) / 2.0
        i = min(range(len(centres)), key=lambda k: abs(centres[k] - cx))
        if abs(centres[i] - cx) <= pitch * 0.75:
            buckets[i].append(w)

    named = []
    for i, cl in enumerate(buckets):
        cl.sort(key=lambda w: (round(w["top"], 1), w["x0"]))
        text = " ".join(w["text"] for w in cl)
        named.append((centres[i], normalise_antibiotic(text), text))

    unresolved = [t or "(no header words)" for _c, d, t in named if d is None]
    if unresolved:
        raise RuntimeError(
            "RC table: column header(s) did not resolve to an antibiotic: "
            "{}".format(unresolved)
        )
    drugs = [d for _c, d, _t in named]
    if len(set(drugs)) != len(drugs):
        raise RuntimeError(
            "RC table: two columns resolved to the same antibiotic: {}".format(drugs)
        )

    out = []
    for i, (cx, drug, _t) in enumerate(named):
        left = (
            cx - pitch / 2.0 - OUTER_PAD
            if i == 0
            else (named[i - 1][0] + cx) / 2.0
        )
        right = (
            cx + pitch / 2.0 + OUTER_PAD
            if i == len(named) - 1
            else (cx + named[i + 1][0]) / 2.0
        )
        out.append(RCColumn(left=left, right=right, antibiotic=drug))
    return out


def _label_column_x(words):
    """Left x of the row-label column: the modal x0 of the RC-label words.

    Prose above the table (e.g. "...observed from RC5 and RC20...") also matches
    RC_LABEL_RE, so a bare "any RC token" scan would put the label boundary in
    the wrong place and poison row banding. The real label column is the tight
    vertical stack, so its x0 is shared by many tokens; a mid-sentence mention
    is not.
    """
    xs = sorted(w["x0"] for w in words if _rc_canon(w["text"]))
    return xs[0] if xs else None


def _row_anchors(words, label_x0):
    """(label, top) for each RC row and the Total row, top to bottom.

    Only labels whose x0 is within a few points of `label_x0` count -- that
    excludes RC mentions in surrounding prose.
    """
    if label_x0 is None:
        return []
    anchors = []
    for w in words:
        if w["x0"] > label_x0 + 18.0:
            continue
        canon = _rc_canon(w["text"])
        if canon:
            anchors.append((canon, w["top"]))
        elif TOTAL_LABEL_RE.match(w["text"].strip()):
            anchors.append(("TOTAL", w["top"]))
    anchors.sort(key=lambda a: a[1])
    out = []
    for label, top in anchors:
        if out and out[-1][0] == label and abs(out[-1][1] - top) < 6:
            continue
        out.append((label, top))
    return out


def _caption_bottom(words, table_number, data_top):
    """Bottom y of this table's own caption line.

    Not merely the first "Table <num>": the 2024 staphylococci page opens with
    a narrative sentence ("As shown in Table 6.3, ...") that also names the
    table, well above the real caption. The real caption is the *last*
    "Table <num>" above where the data starts, so scan for that.
    """
    num = (table_number or "").split()[-1]
    ordered = sorted(range(len(words)), key=lambda i: (words[i]["top"], words[i]["x0"]))
    best = 0.0
    for pos, i in enumerate(ordered):
        w = words[i]
        if w["text"].strip().lower().rstrip(":.") != "table":
            continue
        nxt = words[ordered[pos + 1]]["text"] if pos + 1 < len(ordered) else ""
        if num and not nxt.lstrip().startswith(num):
            continue
        line = [x for x in words if w["top"] - 2 <= x["top"] <= w["top"] + 26]
        line_bottom = max(x["bottom"] for x in line)
        if line_bottom < data_top - 2.0:
            best = max(best, line_bottom)
    return best


def _cells_for_band(words, top, bottom, columns, label_right):
    """{antibiotic: Measurement} for one row band."""
    buckets: dict = {}
    for w in words:
        cy = (w["top"] + w["bottom"]) / 2.0
        if not (top <= cy < bottom):
            continue
        cx = (w["x0"] + w["x1"]) / 2.0
        if cx < label_right:
            continue
        for col in columns:
            if col.left <= cx < col.right:
                buckets.setdefault(col.antibiotic, []).append(w)
                break
    out = {}
    for drug, ws in buckets.items():
        ws.sort(key=lambda w: (round(w["top"], 1), w["x0"]))
        meas = parse_measurement(_join_cell_words(ws))
        if not meas.is_empty:
            out[drug] = meas
    return out


def _extract_rc_page(page, columns=None, table_number=None):
    """Parse one page of an RC-wise table.

    On the caption page `columns` is None and is derived from the header. On a
    continuation page the caller passes the caption page's `columns` (the two
    pages share an identical column layout in these reports).

    Returns (rows, columns) where rows is [(label, {antibiotic: Measurement})]
    with label one of "RC<n>" or "TOTAL".
    """
    words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
    if not words:
        return [], columns

    label_x0 = _label_column_x(words)
    anchors = _row_anchors(words, label_x0)
    if not anchors:
        return [], columns

    # Where the data grid starts: the top of the first "n / N" word sitting to
    # the right of the label column. The RC label baseline sits BELOW its own
    # cell's first line, so it cannot be used for this.
    label_right_guess = label_x0 + 22.0
    frac_tops = [
        w["top"]
        for w in words
        if "/" in w["text"] and (w["x0"] + w["x1"]) / 2.0 > label_right_guess
    ]
    data_top = min(frac_tops) if frac_tops else (anchors[0][1] - 14.0)

    if columns is None:
        cap_bottom = _caption_bottom(words, table_number, data_top)
        centres = _data_column_centres(words, label_right_guess, data_top)
        header_words = [
            w for w in words if cap_bottom < w["top"] < data_top - 1.0
        ]
        columns = _name_columns(header_words, centres)

    label_right = min(c.left for c in columns)
    page_bottom = max(w["bottom"] for w in words)

    # Band each row on its OWN numerator line, not on midpoints between label
    # baselines. RC rows vary in height -- a cell like "1421 / 1866 (76.2)"
    # wraps to three lines while its neighbours are one -- so a midpoint sep can
    # fall inside a tall row and hand its percentage line to the next RC. Every
    # data cell has an "n / N" group, and all of a row's "/" words share a
    # `top`, so clustering those tops recovers one band per row regardless of
    # height. The row's percentage line then always sits between its own "/"
    # line and the next row's.
    slash_tops = sorted(
        w["top"]
        for w in words
        if "/" in w["text"] and (w["x0"] + w["x1"]) / 2.0 > label_right
    )
    row_tops: list[float] = []
    for t in slash_tops:
        if not row_tops or t - row_tops[-1] > 6.0:
            row_tops.append(t)
    if not row_tops:
        return [], columns

    seps = [rt - 4.0 for rt in row_tops] + [page_bottom + 1.0]
    used = set()
    rows = []
    for k, rt in enumerate(row_tops):
        # The label whose baseline is nearest this numerator line.
        li = min(
            range(len(anchors)),
            key=lambda j: abs(anchors[j][1] - rt),
        )
        label = anchors[li][0]
        cells = _cells_for_band(words, seps[k], seps[k + 1], columns, label_right)
        if not cells:
            continue
        if label in used:
            # A numerator that itself wrapped across two lines produced a second
            # band for the same RC; fold it into the first.
            for lbl, existing in rows:
                if lbl == label:
                    existing.update(
                        {d: m for d, m in cells.items() if d not in existing}
                    )
                    break
            continue
        used.add(label)
        rows.append((label, cells))
    return rows, columns


# --- driver ----------------------------------------------------------------


class RCOrganismSpec:
    """Everything organism-specific needed to pull one RC-wise AMS table."""

    def __init__(self, name, pattern, specimen=None, reject=None):
        self.name = name
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.specimen = re.compile(
            specimen or r"\btotal\b|\ball\s+samples\b", re.IGNORECASE
        )
        self.reject = re.compile(reject or r"\bfrom\s+urine\b", re.IGNORECASE)


def parse_rc_report(source, spec: RCOrganismSpec, extracted_date=None):
    """Extract one organism's RC-wise AMS table from one report edition.

    Raises LookupError if the edition has no such table (e.g. E. coli /
    K. pneumoniae in the 2022 edition); the caller decides whether that is
    expected.
    """
    extracted_date = extracted_date or _dt.date.today().isoformat()
    if not source.path.exists():
        raise FileNotFoundError(
            "{} not found. Run `python -m src.fetch --year {}` first.".format(
                source.path, source.report_year
            )
        )

    records: list[RCRecord] = []
    with pdfplumber.open(source.path) as pdf:
        hit = find_rc_caption(
            pdf,
            spec.pattern,
            spec.specimen,
            spec.reject,
            cache_key=str(source.path),
        )

        rows: list = []
        columns = None
        seen_total = False
        # Caption page, then continuation pages until the Total row appears.
        for offset in range(0, 4):
            pi = hit.page_index + offset
            if pi >= len(pdf.pages):
                break
            if offset and _page_text(str(source.path), pi, pdf.pages[pi]) and (
                RC_CAPTION_RE.search(_page_text(str(source.path), pi, pdf.pages[pi]))
            ):
                break  # a new table starts here
            page_rows, columns = _extract_rc_page(
                pdf.pages[pi],
                columns if offset else None,
                table_number=hit.table_number,
            )
            if offset and not page_rows:
                break
            for label, cells in page_rows:
                if label == "TOTAL":
                    seen_total = True
                    continue
                rows.append((label, cells))
            if seen_total:
                break

        if not rows:
            raise RuntimeError(
                "{} {} ({}): located caption but extracted no RC rows".format(
                    source.report_year, hit.table_number, spec.name
                )
            )

        # Fold any RC that appeared twice (a page break, or a numerator that
        # itself wrapped), taking each antibiotic's first non-empty reading.
        merged: dict = {}
        order: list = []
        for label, cells in rows:
            if label not in merged:
                merged[label] = dict(cells)
                order.append(label)
            else:
                for drug, meas in cells.items():
                    merged[label].setdefault(drug, meas)

        drugs = [c.antibiotic for c in columns]
        consistent = mismatched = 0
        for label in order:
            cells = merged[label]
            for drug in drugs:
                meas = cells.get(drug)
                if meas is None:
                    continue
                flags = list(meas.flags)
                if any(f.startswith("pct_mismatch") for f in flags):
                    mismatched += 1
                elif meas.reported_pct is not None:
                    consistent += 1
                records.append(
                    RCRecord(
                        organism=spec.name,
                        regional_centre=label,
                        antibiotic=drug,
                        year=source.report_year,
                        susceptible_n=meas.susceptible_n,
                        tested_n=meas.tested_n,
                        susceptible_pct=meas.reported_pct,
                        source_report_year=source.report_year,
                        source_table=hit.table_number,
                        source_url=source.url,
                        extracted_date=extracted_date,
                        reported_pct=meas.reported_pct,
                        computed_pct=meas.computed_pct,
                        flags=flags,
                    )
                )

        checked = consistent + mismatched
        if checked and consistent / checked < MIN_CONSISTENT:
            raise RuntimeError(
                "{} {} ({}): only {}/{} cells reconcile with their printed %. "
                "Column boundaries are probably wrong -- refusing to emit "
                "(spec section 4.2).".format(
                    source.report_year, hit.table_number, spec.name,
                    consistent, checked,
                )
            )

    if not records:
        raise RuntimeError(
            "{} {} ({}): extracted zero records".format(
                source.report_year, hit.table_number, spec.name
            )
        )
    return records


# Organism registry. E. coli / K. pneumoniae have no RC-wise AMS table in the
# 2022 edition (only a urine one, out of scope); the driver in
# `build_rc_dataset` knows this and does not treat the LookupError as a failure.
SPECS: dict[str, RCOrganismSpec] = {
    "Escherichia coli": RCOrganismSpec(
        name="Escherichia coli",
        pattern=r"\b(?:E\.?\s*coli|Escherichia\s+coli)\b",
    ),
    "Klebsiella pneumoniae": RCOrganismSpec(
        name="Klebsiella pneumoniae",
        pattern=r"\b(?:K\.?\s*pneumoniae?|Klebsiella\s+pneumoniae?)\b",
    ),
    "Staphylococcus aureus": RCOrganismSpec(
        name="Staphylococcus aureus",
        pattern=r"\b(?:S\.?\s*aureus|Staphylococcus\s+aureus)\b",
    ),
}

# The organism has an RC-wise AMS table only in these editions; anything else is
# a real "caption not found" failure.
EXPECTED_EDITIONS: dict[str, set] = {
    "Escherichia coli": {2023, 2024},
    "Klebsiella pneumoniae": {2023, 2024},
    "Staphylococcus aureus": {2022, 2023, 2024},
}
