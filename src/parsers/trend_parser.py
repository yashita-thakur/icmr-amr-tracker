"""Chapter-agnostic driver for the yearly susceptibility trend tables.

Every chapter (Enterobacterales, non-fermenters, staphylococci) is parsed by
this one function. The three failure modes hardened against in `base.py` --
x-coordinate column matching, whole-word cell assembly, and discarding nested
phantom row bands -- are properties of these PDFs, not of any one chapter, and
all of them recur outside Enterobacterales. Sharing the driver means a fix
found in one chapter protects the others automatically.

What differs per chapter is only configuration: how the organism is spelled,
which specimen wording to accept or reject, and which drug panel to expect.
"""

from __future__ import annotations

import datetime as _dt
import re

import pdfplumber

from .antibiotics import normalise_antibiotic
from .base import Record, extract_trend_table, find_caption


class OrganismSpec:
    """Everything chapter-specific needed to pull one organism's trend table."""

    def __init__(
        self,
        name,
        pattern,
        panel,
        specimen=r"all\s+samples",
        reject=r"isolated\s+from\s+urine|\bfrom\s+urine\b|\bfrom\s+blood\b",
        flag_rules=None,
        note=None,
    ):
        self.name = name
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.panel = list(panel)
        self.specimen = re.compile(specimen, re.IGNORECASE)
        self.reject = re.compile(reject, re.IGNORECASE) if reject else None
        # {canonical antibiotic: flag} applied to every record for that drug.
        self.flag_rules = dict(flag_rules or {})
        self.note = note


def parse_report(source, spec: OrganismSpec, extracted_date=None):
    """Extract one organism's yearly trend table from one report edition."""
    extracted_date = extracted_date or _dt.date.today().isoformat()

    if not source.path.exists():
        raise FileNotFoundError(
            "{} not found. Run `python -m src.fetch --year {}` first.".format(
                source.path, source.report_year
            )
        )

    records: list[Record] = []
    with pdfplumber.open(source.path) as pdf:
        hit = find_caption(
            pdf,
            spec.pattern,
            spec.specimen,
            spec.reject,
            cache_key=str(source.path),
        )
        page = pdf.pages[hit.page_index]
        table = extract_trend_table(
            page, label_ok=lambda text: normalise_antibiotic(text) is not None
        )

        data_rows = table.data_rows()
        first_data = None
        for ri in data_rows:
            if table.row_has_fraction(ri):
                first_data = ri
                break
        if first_data is None:
            raise RuntimeError(
                "{} {} ({}): no row on page {} carried a numerator/denominator".format(
                    source.report_year,
                    hit.table_number,
                    spec.name,
                    table.page_number,
                )
            )

        # Group rows into antibiotics. A label can wrap across two rows --
        # "Piperacillin-" on the value row and "tazobactam" on the next -- and
        # neither half resolves alone, so rows are accumulated until their
        # combined label names a drug we recognise.
        entries: list[dict] = []
        pending_rows: list[int] = []
        pending_labels: list[str] = []
        for ri in [r for r in data_rows if r >= first_data]:
            pending_rows.append(ri)
            label = table.row_label(ri)
            if label:
                pending_labels.append(label)
            name = normalise_antibiotic(" ".join(pending_labels))
            if name:
                entries.append(
                    {
                        "antibiotic": name,
                        "rows": list(pending_rows),
                        "label": " ".join(pending_labels),
                    }
                )
                pending_rows, pending_labels = [], []

        resolved = [
            (
                e["antibiotic"],
                list(table.measurements_for_rows(e["rows"])),
                ["label_footnote_asterisk"] if "*" in e["label"] else [],
            )
            for e in entries
        ]

        # Fallback: the label column failed entirely. Assign positionally only
        # when the data-row count matches the expected panel exactly, and flag
        # every record so produced so it can never pass as a read label.
        if not resolved:
            fraction_rows = [
                ri
                for ri in data_rows
                if ri >= first_data and table.row_has_fraction(ri)
            ]
            if len(fraction_rows) != len(spec.panel):
                raise RuntimeError(
                    "{} {} ({}): could not read antibiotic labels, and found {} "
                    "data rows against an expected panel of {}. Refusing to "
                    "guess.".format(
                        source.report_year,
                        hit.table_number,
                        spec.name,
                        len(fraction_rows),
                        len(spec.panel),
                    )
                )
            resolved = [
                (
                    name,
                    list(table.measurements_for_rows([ri])),
                    ["antibiotic_assigned_positionally"],
                )
                for name, ri in zip(spec.panel, fraction_rows)
            ]

        found = {name for name, _m, _f in resolved}
        missing = [a for a in spec.panel if a not in found]
        if missing:
            raise RuntimeError(
                "{} {} ({}): expected panel drug(s) {} not found; resolved {}. "
                "Refusing to emit a partial panel -- check the table or update "
                "the panel.".format(
                    source.report_year,
                    hit.table_number,
                    spec.name,
                    missing,
                    sorted(found),
                )
            )

        seen_pairs = set()
        for antibiotic, measurements, extra_flags in resolved:
            rule_flag = spec.flag_rules.get(antibiotic)
            for year, meas, geom_flags in measurements:
                if (antibiotic, year) in seen_pairs:
                    continue
                seen_pairs.add((antibiotic, year))
                flags = list(meas.flags) + geom_flags + list(extra_flags)
                if rule_flag:
                    flags.append(rule_flag)
                records.append(
                    Record(
                        organism=spec.name,
                        antibiotic=antibiotic,
                        year=year,
                        susceptible_n=meas.susceptible_n,
                        tested_n=meas.tested_n,
                        # Only ever what the source printed; see base.py.
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

    if not records:
        raise RuntimeError(
            "{} {} ({}): extracted zero records".format(
                source.report_year, hit.table_number, spec.name
            )
        )
    return records
