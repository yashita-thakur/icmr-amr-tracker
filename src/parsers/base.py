"""Shared machinery for locating and parsing AMRSN yearly-trend tables.

Design notes (these encode findings from the source PDFs, spec section 4):

* Table NUMBERS are not stable across report editions. Enterobacterales is
  Chapter 3 in the 2022 and 2023 editions (Tables 3.6 / 3.7) but Chapter 2 in
  the 2024 edition (Tables 2.6 / 2.7). We therefore locate tables by matching
  their CAPTION TEXT and read the table number back out of the caption, rather
  than hardcoding either a number or a page. The recovered number is what gets
  written to `source_table`, so every row cites the number genuinely printed in
  that edition.

* Organism names are not spelled consistently either -- the 2022 edition prints
  "Klebsiella pneumonia" (without the trailing e). Organism patterns must
  tolerate this.

* The extracted text layer of these PDFs does NOT preserve row/column
  alignment: antibiotic labels and their values land in separate blocks, and
  later year columns are vertically offset. Regex over `page.extract_text()`
  therefore silently mis-assigns values to the wrong antibiotic. All extraction
  goes through pdfplumber's ruling-line table detection. Per spec section 4.2
  this is deliberate: if the table strategies below all fail we raise, rather
  than degrade to text-regex.

* Values are matched to years by X-COORDINATE, not by column index. Column
  indices are not trustworthy: in the 2023 edition the header row carries an
  extra leading cell, so "Year-2017" sits at column index 4 while its own data
  sits at column index 3. Indexing by column silently pairs each antibiotic
  with the wrong year (or, as first observed, drops the whole table).

* Cell contents are assembled from WORDS, not from pdfplumber's per-cell text.
  See the `TrendTable` docstring: the 2022 edition's ruled cells are narrower
  than the digits printed in them, and per-cell text silently loses the
  overhanging characters.

* Antibiotic labels wrap. "Piperacillin-tazobactam" is printed as
  "Piperacillin-" on the value row and "tazobactam" on a following row, and
  neither half resolves alone, so rows are accumulated until their combined
  label names a known drug.

* Vertically merged cells produce nested phantom rows that repeat a value and,
  unfiltered, corrupt the NEXT antibiotic. Contained row bands are discarded.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

# --- schema (spec section 3) ------------------------------------------------


@dataclass
class Record:
    organism: str
    antibiotic: str
    year: int
    susceptible_n: int | None
    tested_n: int | None
    susceptible_pct: float | None
    source_report_year: int
    source_table: str
    source_url: str
    extracted_date: str
    # Provenance / quality annotations beyond the minimal spec schema.
    reported_pct: float | None = None
    computed_pct: float | None = None
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["flags"] = ",".join(self.flags)
        return d


FIELDNAMES = [
    "organism",
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


# --- caption location -------------------------------------------------------

# Caption grammar is not uniform across chapters or editions. Three variants
# occur, and a parser built for only the first silently finds nothing in the
# other two chapters:
#
#   "Table 2.6: Yearly susceptibility trend of E. coli isolated from ..."
#       -- Enterobacterales, all editions; NFGNB in 2023/2024.
#   "Table 5.6: Yearly susceptible trend of A. baumannii isolated from ..."
#       -- NFGNB in the 2022 edition ("susceptible", not "susceptibility").
#   "Table 6.4: Year-wise susceptibility trends of S. aureus from all samples"
#       -- Staphylococci, all editions ("Year-wise"/"Year wise", not "Yearly",
#          and no "isolated" before "from").
#
# Table numbers may also carry a letter suffix (e.g. 1.12b) elsewhere in the
# reports, so the number pattern allows one.
CAPTION_RE = re.compile(
    r"Table\s*(?P<table>\d+\.\d+[a-z]?)\s*[:.]?\s*"
    r"(?:Yearly|Year[\s\-‐‑‒–—―]*wise)\s+"
    r"(?:susceptibility|susceptible)\s+trends?\s+(?:of\s+)?"
    r"(?P<rest>.{0,140})",
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class CaptionHit:
    page_index: int
    table_number: str
    caption: str


# Locating a caption means extracting text page by page until it is found. With
# five organisms per edition that repeats the same expensive extraction on the
# same pages up to five times over, which dominates total runtime on the 42 MB
# 2022 PDF. Page text is therefore memoised by (file, page index) -- lazily, so
# a caption near the front still short-circuits rather than paying to read the
# whole document up front.
_PAGE_TEXT_CACHE: dict = {}


def _page_text(cache_key, index, page) -> str:
    if cache_key is None:
        return page.extract_text() or ""
    key = (cache_key, index)
    cached = _PAGE_TEXT_CACHE.get(key)
    if cached is None:
        cached = page.extract_text() or ""
        _PAGE_TEXT_CACHE[key] = cached
    return cached


def find_caption(
    pdf,
    organism_pattern: re.Pattern,
    specimen_pattern: re.Pattern,
    reject_pattern: re.Pattern | None = None,
    cache_key=None,
) -> CaptionHit:
    """Find the page whose text carries the target table's caption.

    Matches on caption semantics, not on table number or page number.
    """
    near_misses: list[str] = []
    for i, page in enumerate(pdf.pages):
        text = _page_text(cache_key, i, page)
        # Cheap pre-filter before running the full caption regex. It must stay
        # in step with CAPTION_RE: an earlier version tested for the literal
        # "usceptibility trend", which silently skipped every page of the 2022
        # non-fermenter chapter, where the captions read "susceptible trend".
        # The tables were found by the regex but never reached it.
        lowered = text.lower()
        if "trend" not in lowered or "susceptib" not in lowered:
            continue
        for m in CAPTION_RE.finditer(text):
            rest = " ".join(m.group("rest").split())
            if not organism_pattern.search(rest):
                continue
            label = "p{} Table {}: {}".format(i + 1, m.group("table"), rest[:70])
            if reject_pattern is not None and reject_pattern.search(rest):
                near_misses.append(label)
                continue
            if not specimen_pattern.search(rest):
                near_misses.append(label)
                continue
            return CaptionHit(
                page_index=i,
                table_number="Table " + m.group("table"),
                caption=" ".join(("Yearly susceptibility trend of " + rest).split()),
            )

    detail = "\n  ".join(near_misses) if near_misses else "(no near misses)"
    raise LookupError(
        "Could not locate a table caption matching organism={!r} specimen={!r}."
        "\nNear misses:\n  {}".format(
            organism_pattern.pattern, specimen_pattern.pattern, detail
        )
    )


# --- cell parsing -----------------------------------------------------------

FRACTION_RE = re.compile(r"(?P<star>\*)?\s*(?P<num>\d[\d,]*)\s*/\s*(?P<den>\d[\d,]*)")
PCT_RE = re.compile(r"\(\s*(?P<pct>\d+(?:\.\d+)?)\s*%?\s*\)")
NULL_PCT_RE = re.compile(r"\(\s*[-‐‑‒–—―]\s*\)")
YEAR_RE = re.compile(r"Year\s*[-‐‑‒–—―]?\s*(?P<year>20\d{2})")

# Table 6.9 (MRSA) wraps its header: the word "Year-" sits on one line and the
# digits on the next, so no single cell reads "Year-2018". Detecting only
# "Year-NNNN" finds 5 of 8 columns there and drops the rest. A header cell that
# is nothing but a plausible surveillance year is therefore also accepted.
# Requiring a whole-cell match keeps data cells (which always carry "/" and a
# bracketed percentage) from being mistaken for headers.
BARE_YEAR_RE = re.compile(r"^(?:Year\s*[-‐‑‒–—―]?\s*)?(?P<year>20(?:1[4-9]|[2-3]\d))$")


def header_year(cell_text: str):
    """Year named by a header cell, or None."""
    m = YEAR_RE.search(cell_text)
    if m:
        return int(m.group("year"))
    m = BARE_YEAR_RE.match(cell_text)
    if m:
        return int(m.group("year"))
    return None

# Percentage agreement tolerance, in percentage points. ICMR rounds to 1-2 d.p.,
# so a gap beyond this means we have paired the wrong numerator with the wrong
# denominator -- exactly the failure a text-regex parser produces silently. We
# surface it instead.
PCT_TOLERANCE = 0.15


@dataclass
class Measurement:
    susceptible_n: int | None = None
    tested_n: int | None = None
    reported_pct: float | None = None
    computed_pct: float | None = None
    flags: list[str] = field(default_factory=list)
    raw: str = ""

    @property
    def is_empty(self) -> bool:
        return self.susceptible_n is None and self.reported_pct is None


def _int(s: str) -> int:
    return int(s.replace(",", ""))


def parse_measurement(cell) -> Measurement:
    """Parse one data cell, e.g. '7587 / 12061 (62.9)' or '*0/8 (-)'."""
    if cell is None:
        return Measurement()
    raw = " ".join(str(cell).split())
    m = Measurement(raw=raw)
    if not raw:
        return m

    frac = FRACTION_RE.search(raw)
    if frac:
        m.susceptible_n = _int(frac.group("num"))
        m.tested_n = _int(frac.group("den"))
        if frac.group("star"):
            # ICMR marks very low isolate counts with a leading asterisk.
            m.flags.append("low_isolate_count_asterisk")
        if m.tested_n:
            m.computed_pct = round(100.0 * m.susceptible_n / m.tested_n, 2)
        else:
            # Genuinely printed in the source: K. pneumoniae / cefazolin / 2018
            # is "*0/0 (-)" -- the drug was not tested against a single isolate
            # that year. No percentage exists, and none is derivable.
            m.flags.append("no_isolates_tested")

    pct = PCT_RE.search(raw)
    if pct:
        m.reported_pct = float(pct.group("pct"))
    elif NULL_PCT_RE.search(raw):
        m.flags.append("pct_suppressed_in_source")

    if m.reported_pct is not None and m.computed_pct is not None:
        if abs(m.reported_pct - m.computed_pct) > PCT_TOLERANCE:
            m.flags.append(
                "pct_mismatch(reported={},computed={})".format(
                    m.reported_pct, m.computed_pct
                )
            )
    return m


# --- table extraction -------------------------------------------------------

TABLE_STRATEGIES = [
    {"vertical_strategy": "lines", "horizontal_strategy": "lines"},
    {"vertical_strategy": "lines", "horizontal_strategy": "text"},
    {"vertical_strategy": "text", "horizontal_strategy": "lines"},
]

def _join_cell_words(words) -> str:
    """Join a cell's words, reattaching numbers broken across a line break.

    Narrow columns in the 2024 MRSA table wrap a number mid-digits: the cell
    holding "4286/4311 (99.4)" emits "4286/431" on one line and a lone "1" on
    the next. Joining on whitespace yields "4286/431", a denominator short by
    one digit and a susceptibility of 994%. So when a line ends on a digit and
    the next line begins with one, the two are spliced rather than spaced.

    Percentages are always parenthesised in these tables, so a leading "(" is
    never treated as a continuation.
    """
    out = ""
    prev_top = None
    for w in words:
        text = w["text"]
        if not out:
            out = text
        elif (
            prev_top is not None
            and round(w["top"], 1) != prev_top
            and out[-1].isdigit()
            and text[:1].isdigit()
        ):
            out += text  # wrapped number: splice, do not space
        else:
            out += " " + text
        prev_top = round(w["top"], 1)
    return out


def _norm(cell) -> str:
    return " ".join(str(cell).split()) if cell else ""


@dataclass
class TrendTable:
    """A located yearly-trend grid, with the geometry needed to read it safely.

    Cell TEXT is not taken from the ruling grid. In the 2022 edition the ruled
    box around the final year column is narrower than the digits printed inside
    it, so pdfplumber's per-cell text drops the characters that overhang:
    "5170 / 14729" comes back as "170 / 1472", and "9980 / 14304" as
    "980 / 1430". The percentage survives, so the cell still looks plausible
    while the counts are silently wrong by an order of magnitude.

    We therefore use the ruling grid only for STRUCTURE (row bands, and the
    x-position of each year header) and read cell contents by assigning whole
    WORDS to a row band and year column by their centre point. Words are
    extracted intact, so no digit can be clipped.
    """

    grid: list  # list[list[str | None]] -- cell text, kept for header detection
    boxes: list  # list[list[tuple | None]] -- cell bboxes, parallel to grid
    year_spans: list  # list[(x0, x1, year)] taken from the header row
    header_row: int
    settings: dict
    page_number: int
    row_bands: list  # (top, bottom) per grid row
    words: list  # page words, each a dict with x0/x1/top/bottom/text
    col_bounds: list  # (left, right, year), boundaries widened to midpoints
    label_right: float  # everything whose centre is left of this is a label
    primary_rows: list  # row indices that are not nested inside another row

    @property
    def years(self) -> list:
        return sorted(y for _l, _r, y in self.col_bounds)

    def _row_words(self, ri: int):
        top, bottom = self.row_bands[ri]
        for w in self.words:
            cy = (w["top"] + w["bottom"]) / 2.0
            if top <= cy < bottom:
                yield w

    def row_label(self, ri: int) -> str:
        """Text left of the first year column, in reading order."""
        picked = [
            w
            for w in self._row_words(ri)
            if (w["x0"] + w["x1"]) / 2.0 < self.label_right
        ]
        picked.sort(key=lambda w: (round(w["top"], 1), w["x0"]))
        return " ".join(w["text"] for w in picked).strip()

    def measurements_for_rows(self, row_indices):
        """Yield (year, Measurement, flags) across a group of rows.

        One antibiotic can occupy more than one grid row (a wrapped label, or a
        numerator line and a percentage line split by a ruling), so parsing is
        done once over the whole group rather than row by row.
        """
        by_year = {}
        for ri in row_indices:
            for w in self._row_words(ri):
                cx = (w["x0"] + w["x1"]) / 2.0
                if cx < self.label_right:
                    continue
                for left, right, year in self.col_bounds:
                    if left <= cx < right:
                        by_year.setdefault(year, []).append(w)
                        break

        for year in sorted(by_year):
            ws = sorted(by_year[year], key=lambda w: (round(w["top"], 1), w["x0"]))
            meas = parse_measurement(_join_cell_words(ws))
            if meas.is_empty:
                continue
            yield year, meas, []

    def row_measurements(self, ri: int):
        """Yield (year, Measurement, flags) for a single row."""
        return self.measurements_for_rows([ri])

    def data_rows(self):
        """Row indices below the header, excluding nested duplicate bands."""
        return [ri for ri in self.primary_rows if ri > self.header_row]

    def row_has_fraction(self, ri: int) -> bool:
        for w in self._row_words(ri):
            if (w["x0"] + w["x1"]) / 2.0 < self.label_right:
                continue
            if "/" in w["text"]:
                return True
        return False


# Outer edges of the first and last year column are widened by this many points,
# since those columns have no neighbour to split the difference with.
OUTER_PAD = 10.0


def _column_bounds(spans):
    """Turn year header x-spans into gapless column boundaries (midpoints)."""
    spans = sorted(spans, key=lambda s: s[0])
    bounds = []
    for i, (x0, x1, year) in enumerate(spans):
        left = x0 - OUTER_PAD if i == 0 else (spans[i - 1][1] + x0) / 2.0
        right = (
            x1 + OUTER_PAD if i == len(spans) - 1 else (x1 + spans[i + 1][0]) / 2.0
        )
        bounds.append((left, right, year))
    return bounds


def _build(page, settings):
    """Turn one extraction strategy's output into TrendTable candidates."""
    try:
        tables = page.find_tables(settings)
    except Exception:  # noqa: BLE001 - a strategy failing is expected
        return []

    try:
        words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
    except Exception:  # noqa: BLE001
        return []

    out = []
    for table in tables or []:
        try:
            grid = table.extract()
        except Exception:  # noqa: BLE001
            continue
        rows = list(table.rows)
        boxes = [list(r.cells) for r in rows]
        if len(boxes) != len(grid):
            continue

        # Header row = the row carrying the most Year-YYYY labels.
        # Year headers can be split across more than one grid row. Table 6.9
        # (MRSA) puts "Year-2020" on the first header row but the remaining
        # seven years as bare digits on the second. Taking whichever single row
        # has the most years would silently drop 2020, and the midpoint column
        # boundaries would then hand 2020's data to its neighbours. So years are
        # accumulated across the header band, first occurrence winning, and we
        # stop as soon as a row carries actual data.
        spans_by_year: dict = {}
        best_hdr = -1
        for ri in range(min(len(grid), 8)):
            row_has_data = any(
                FRACTION_RE.search(_norm(t)) for t in grid[ri] if t
            )
            if row_has_data:
                break
            found = False
            for text, box in zip(grid[ri], boxes[ri]):
                year = header_year(_norm(text))
                if year is not None and box is not None and year not in spans_by_year:
                    spans_by_year[year] = (box[0], box[2], year)
                    found = True
            if found:
                best_hdr = ri
        best_spans = [spans_by_year[y] for y in sorted(spans_by_year)]
        if len(best_spans) < 3:
            continue

        bands = []
        for r in rows:
            bb = r.bbox
            bands.append((bb[1], bb[3]))

        # A vertically merged cell makes pdfplumber report a nested extra row:
        # the wrapped "Piperacillin- / tazobactam" label produces a sub-band
        # sitting entirely inside the real data row, and that sub-band repeats
        # the row's percentage. Left in, it gets absorbed by the NEXT
        # antibiotic's group and silently overwrites its percentage. Keep only
        # bands that are not contained within another band.
        primary = []
        for i, (top_i, bot_i) in enumerate(bands):
            nested = False
            for j, (top_j, bot_j) in enumerate(bands):
                if i == j:
                    continue
                bigger = (bot_j - top_j) > (bot_i - top_i)
                if bigger and top_j <= top_i + 0.5 and bot_i <= bot_j + 0.5:
                    nested = True
                    break
            if not nested:
                primary.append(i)

        col_bounds = _column_bounds(best_spans)
        out.append(
            TrendTable(
                grid=grid,
                boxes=boxes,
                year_spans=best_spans,
                header_row=best_hdr,
                settings=settings,
                page_number=page.page_number,
                row_bands=bands,
                words=words,
                col_bounds=col_bounds,
                label_right=col_bounds[0][0],
                primary_rows=primary,
            )
        )
    return out


def score_trend_table(tt: TrendTable, label_ok=None) -> int:
    """How WELL-FORMED is this grid? Not merely how many cells it has.

    Counting raw data cells is an actively bad metric here. The `lines/text`
    strategy splits each printed line into its own row, so "3424/6030" and
    "(56.8)" land in different rows and every antibiotic label drifts away from
    its numbers. That shredded grid contains *more* non-empty cells than the
    correct one and would win a naive count, while being unusable.

    The `text` vertical strategy fails differently and more insidiously: it
    puts column boundaries in the wrong places, slicing digits off the numbers
    themselves. "9980 / 14304" becomes "9" at the end of one cell and
    "980 / 14304" in the next; "7587 / 12061" becomes "587 / 1206". Every cell
    still looks well-formed.

    The tell is arithmetic. A cell that has lost a digit no longer agrees with
    its own printed percentage, so we score each grid on whether it is
    INTERNALLY CONSISTENT and penalise disagreement hard. A correctly cut grid
    reconciles; a mis-cut one does not.

    We also reward rows whose label resolves to a real antibiotic while
    carrying data.
    """
    consistent = 0
    inconsistent = 0
    labelled_rows = 0
    for ri in tt.data_rows():
        measurements = list(tt.row_measurements(ri))
        for _year, meas, _flags in measurements:
            if any(f.startswith("pct_mismatch") for f in meas.flags):
                inconsistent += 1
            elif meas.susceptible_n is not None and (
                meas.reported_pct is not None
                or "pct_suppressed_in_source" in meas.flags
            ):
                consistent += 1
        if measurements and label_ok is not None and label_ok(tt.row_label(ri)):
            labelled_rows += 1
    return (
        labelled_rows * 100
        + consistent * 3
        - inconsistent * 10
        + len(tt.year_spans)
    )


def extract_trend_table(page, label_ok=None) -> TrendTable:
    """Try each ruling strategy; return the best-formed trend grid.

    `label_ok` is an optional callable taking a row's label text and returning
    True if it names something the caller recognises; supplying it materially
    improves strategy selection.

    Raises if none produce a usable grid. Per spec section 4.2 we do NOT fall
    back to regex over raw text -- that path silently mis-aligns rows.
    """
    best, best_score = None, 0
    for settings in TABLE_STRATEGIES:
        for tt in _build(page, settings):
            s = score_trend_table(tt, label_ok)
            if s > best_score:
                best, best_score = tt, s

    if best is None:
        raise RuntimeError(
            "pdfplumber could not resolve a yearly-trend grid on page {}.\n"
            "STOP: do not fall back to regex over raw text (spec section 4.2) -- "
            "the text layer of these PDFs does not preserve row/column "
            "alignment. Switching table-extraction library (e.g. to camelot-py) "
            "is a decision to raise with the maintainer first.".format(
                page.page_number
            )
        )
    return best
