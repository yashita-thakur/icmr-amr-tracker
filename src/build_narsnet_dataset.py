"""Orchestrate parse -> validate -> export for the NCDC NARS-Net tables (V3).

Usage:
    python -m src.build_narsnet_dataset            # parse what is in data/raw/
    python -m src.build_narsnet_dataset --fetch    # download first, then parse
    python -m src.build_narsnet_dataset --strict   # exit non-zero on fixture failure
    python -m src.build_narsnet_dataset --year 2019 --organism "Escherichia coli"

Exports to data/processed/:
    narsnet_trends.csv             one row per organism x antibiotic x specimen x edition
    narsnet_trends.json            same, as a JSON array
    narsnet_panel.json             drug panel and specimen columns per edition
    narsnet_revisions.json         structurally empty; see its own `note` field
    narsnet_extraction_report.json run metadata, checks, and the composite-column report

**The filenames deliberately drop the `amr_` prefix that the AMRSN exports
carry.** These two datasets are not concatenable and share no comparison
column: NARS-Net publishes % resistant, AMRSN publishes % susceptible, and
AMRSN publishes no % intermediate for E. coli or S. aureus, so an AMRSN
% resistant cannot be computed. `amr_trends.csv` and `narsnet_trends.csv` can be
read side by side as parallel series and must never be joined on a single shared
value. A reader who has only the filenames should be able to tell that much.

Scope is the 2019 and 2020 editions, E. coli and S. aureus -- the editions whose
printed numerator is complete enough that every cell can be checked against its
own printed percentage. See `parsers/narsnet_parser.py` for why the later
editions are not claimed yet.
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import sys

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from .narsnet_validate import (
    REVISIONS_NOTE,
    apply_degenerate_composite_flags,
    apply_narsnet_panel_flags,
    check_narsnet_fixtures,
    detect_narsnet_panel_changes,
    find_narsnet_cross_report_revisions,
    internal_consistency,
    narsnet_panel_by_edition,
    summarise_composite_sums,
)
from .parsers.narsnet_parser import (
    NARSNET_FIELDNAMES,
    SPECS,
    parse_narsnet_report,
)
from .sources import ATTRIBUTION, NARSNET_SOURCES, PROCESSED_DIR

# Editions this builder covers. Kept here rather than derived from
# NARSNET_SOURCES, which holds all eight: the registry records what can be
# fetched, this records what has been verified against a hand-read of the page.
BUILD_YEARS = [2020, 2019]

ORGANISMS = list(SPECS)

# Every (edition, organism) pair a complete build covers.
FULL_SCOPE = {(year, organism) for year in BUILD_YEARS for organism in ORGANISMS}


def coverage(records):
    """The (edition, organism) pairs actually present in `records`."""
    return {(r.source_report_year, r.organism) for r in records}


def is_complete(records) -> bool:
    """Whether `records` covers the builder's whole scope.

    Derived from the records rather than from the CLI arguments, so a parse that
    failed halfway counts as incomplete for the same reason a `--year` filter
    does. In both cases the resulting dataset is a subset, and a subset must not
    land on the canonical filenames.
    """
    return coverage(records) == FULL_SCOPE


def build(fetch_first: bool = False, years=None, organisms=None):
    years = sorted(years or BUILD_YEARS, reverse=True)
    organisms = organisms or ORGANISMS
    extracted_date = _dt.date.today().isoformat()

    if fetch_first:
        from .fetch import fetch_one

        print("== fetch ==")
        for y in years:
            fetch_one(NARSNET_SOURCES[y])
        print()

    print("== parse ==")
    records = []
    parsed, failed = [], []
    for year in years:
        source = NARSNET_SOURCES[year]
        for organism in organisms:
            try:
                got = parse_narsnet_report(source, SPECS[organism], extracted_date)
            except Exception as exc:  # noqa: BLE001 - report and continue
                print("  [FAILED]   {} {}: {}".format(year, organism, exc))
                failed.append(
                    {"report_year": year, "organism": organism, "error": str(exc)}
                )
                continue
            records.extend(got)
            table = got[0].source_table
            print(
                "  [ok]       {} {:<22} {:<9} {:>3} rows".format(
                    year, organism, table, len(got)
                )
            )
            parsed.append(
                {
                    "report_year": year,
                    "organism": organism,
                    "source_table": table,
                    "rows": len(got),
                    "specimens": sorted({r.specimen for r in got}),
                }
            )
    print()

    return records, parsed, failed, extracted_date


def export(records, parsed, failed, extracted_date):
    """Validate, then write -- but only if the build covers the whole scope.

    Returns (fixture_failures, wrote). `wrote` is False when the build was
    narrowed by --year/--organism or cut short by a parse failure; the checks
    still run and still print, so a narrow build remains useful as a fast check,
    but nothing is written. Refusing to write was chosen over writing to a
    `.partial` filename because it leaves nothing behind: no second set of paths
    to gitignore, and no half-scope artefact that a later reader could mistake
    for the dataset.
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print("== validate ==")
    passes, failures = check_narsnet_fixtures(records)
    print("  fixtures            {} passed, {} failed".format(len(passes), len(failures)))
    for f in failures:
        print("    [FAIL] {}".format(f))

    mismatches = internal_consistency(records)
    print(
        "  printed %R vs counts {} row(s) disagree beyond the printed precision".format(
            len(mismatches)
        )
    )
    for r in sorted(mismatches, key=lambda r: (r.source_report_year, r.organism, r.antibiotic)):
        detail = next(f for f in r.flags if f.startswith("pct_mismatch"))
        print(
            "    {} {} {} / {}: {}".format(
                r.source_report_year, r.organism, r.antibiotic, r.specimen, detail
            )
        )

    degenerate = apply_degenerate_composite_flags(records)
    print("  cross-column        {} degenerate composite disagreement(s)".format(len(degenerate)))
    for d in degenerate:
        print(
            "    {} {} {}: {} and {} share N={} but print {} and {} resistant".format(
                d["source_report_year"], d["organism"], d["antibiotic"],
                d["composite_specimen"], d["only_reported_stratum"],
                d["shared_tested_n"], d["composite_resistant_n"],
                d["stratum_resistant_n"],
            )
        )

    changes = apply_narsnet_panel_flags(records)
    print("  panel / specimens   {} change(s) between consecutive editions".format(len(changes)))
    for c in changes:
        bits = []
        for label, key in (
            ("drugs +", "antibiotics_added"),
            ("drugs -", "antibiotics_removed"),
            ("specimens +", "specimen_columns_added"),
            ("specimens -", "specimen_columns_removed"),
        ):
            if c[key]:
                bits.append("{}{}".format(label, c[key]))
        print(
            "    {} {}->{}: {}".format(
                c["organism"], c["from_edition"], c["to_edition"], "; ".join(bits)
            )
        )

    revisions = find_narsnet_cross_report_revisions(records)
    print("  cross-edition       {} revision(s) (empty by design)".format(len(revisions)))
    composites = summarise_composite_sums(records)
    print("  composite columns   {} row(s) summarised, no flag raised".format(len(composites)))
    print()

    if not is_complete(records):
        missing = sorted(FULL_SCOPE - coverage(records), key=str)
        print("== export ==")
        for line in (
            "  [REFUSED]  This build does not cover the builder's whole "
            "scope, so nothing was written.",
            "             Missing: {}".format(missing),
            "             The checks above still ran and are still valid "
            "for what was parsed.",
            "             To regenerate the dataset, re-run with no --year "
            "or --organism filter:",
            "                 python -m src.build_narsnet_dataset",
            "             The canonical narsnet_* files in data/processed/ "
            "are untouched.",
        ):
            print(line)
        return failures, False

    print("== export ==")
    rows = [r.to_dict() for r in records]
    rows.sort(
        key=lambda d: (
            d["organism"],
            d["antibiotic"],
            d["specimen"],
            d["source_report_year"],
        )
    )

    csv_path = PROCESSED_DIR / "narsnet_trends.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=NARSNET_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    json_path = PROCESSED_DIR / "narsnet_trends.json"
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2)

    panel = narsnet_panel_by_edition(records)
    panel_path = PROCESSED_DIR / "narsnet_panel.json"
    with open(panel_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "description": (
                    "The drug panel and the specimen columns each NARS-Net "
                    "edition prints, per organism. Both axes change "
                    "independently and both matter: between the 2019 and 2020 "
                    "editions the E. coli drug panel is identical while the "
                    "pooled specimen column disappears, so an edition-over-"
                    "edition comparison of a pooled figure would be comparing a "
                    "printed column against one that is no longer printed."
                ),
                "attribution": ATTRIBUTION,
                "generated": extracted_date,
                "panel": panel,
                "changes": detect_narsnet_panel_changes(panel),
            },
            fh,
            indent=2,
        )

    rev_path = PROCESSED_DIR / "narsnet_revisions.json"
    with open(rev_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "description": (
                    "Same (organism, antibiotic, specimen, year) reported with "
                    "different percentages by different NARS-Net editions."
                ),
                "note": REVISIONS_NOTE,
                "attribution": ATTRIBUTION,
                "generated": extracted_date,
                "count": len(revisions),
                "revisions": revisions,
            },
            fh,
            indent=2,
        )

    rep_path = PROCESSED_DIR / "narsnet_extraction_report.json"
    with open(rep_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "generated": extracted_date,
                "network": "narsnet",
                "attribution": ATTRIBUTION,
                "metric": (
                    "Every value in this dataset is PERCENT RESISTANT. The AMRSN "
                    "dataset in amr_trends.csv is percent susceptible, and AMRSN "
                    "publishes no percent intermediate for E. coli or S. aureus, "
                    "so an AMRSN percent resistant cannot be computed. The two "
                    "datasets are parallel series and must never be joined on a "
                    "single shared comparison value."
                ),
                "scope": (
                    "The 2019 and 2020 editions, E. coli and S. aureus. These are "
                    "the editions whose printed numerator is complete enough that "
                    "every cell can be checked against its own printed "
                    "percentage. The 2021 edition prints a partly corrupt "
                    "numerator and the 2022-2024 editions print none."
                ),
                "total_rows": len(records),
                "sources": [
                    {
                        "report_year": s.report_year,
                        "reporting_period": s.edition,
                        "cover_year": s.cover_year,
                        "url": s.url,
                        "sha256": s.sha256,
                    }
                    for s in sorted(
                        (NARSNET_SOURCES[y] for y in BUILD_YEARS),
                        key=lambda s: s.report_year,
                        reverse=True,
                    )
                ],
                "parsed": parsed,
                "failed": failed,
                "fixtures": {
                    "passed": len(passes),
                    "failed": len(failures),
                    "failures": failures,
                },
                "printed_pct_vs_printed_counts": {
                    "description": (
                        "Cells whose printed percentage does not follow from "
                        "their own printed counts, allowing half the printed "
                        "precision for rounding. All are carried exactly as "
                        "printed and flagged; nothing is corrected."
                    ),
                    "count": len(mismatches),
                    "rows": [
                        {
                            "organism": r.organism,
                            "antibiotic": r.antibiotic,
                            "specimen": r.specimen,
                            "source_report_year": r.source_report_year,
                            "tested_n": r.tested_n,
                            "resistant_n": r.resistant_n,
                            "reported_pct": r.reported_pct,
                            "computed_pct": r.computed_pct,
                        }
                        for r in sorted(
                            mismatches,
                            key=lambda r: (
                                r.source_report_year,
                                r.organism,
                                r.antibiotic,
                                r.specimen,
                            ),
                        )
                    ],
                },
                "cross_column_checks": {
                    "degenerate_composites": {
                        "description": (
                            "A composite column covering exactly one reported "
                            "stratum, because the drug's other specimen blocks "
                            "are greyed out. The two columns describe the same "
                            "isolates, so their counts must agree. Where they do "
                            "not, both rows are flagged and both figures are "
                            "kept as printed."
                        ),
                        "count": len(degenerate),
                        "findings": degenerate,
                    },
                    "composite_vs_partition_sums": {
                        "description": (
                            "Composite columns against the sum of the columns "
                            "that partition them. NO FLAG IS RAISED FROM THIS. "
                            "The difference is systematic rather than "
                            "exceptional -- in the 2019 edition every pooled "
                            "denominator equals its partition sum exactly while "
                            "no pooled numerator does, and in the 2020 edition "
                            "neither does -- so flagging it would mark nearly "
                            "every composite row and bury the findings that are "
                            "genuinely anomalous. The reports do not state that "
                            "a pooled column is the arithmetic sum of the "
                            "columns beside it; the strata are separately "
                            "de-duplicated and separately computed. The measured "
                            "differences are recorded here so their size can be "
                            "judged rather than assumed."
                        ),
                        "count": len(composites),
                        "rows": composites,
                    },
                },
                "panel_changes": changes,
                "revisions": {"count": len(revisions), "note": REVISIONS_NOTE},
            },
            fh,
            indent=2,
        )

    for path in (csv_path, json_path, panel_path, rev_path, rep_path):
        print("  wrote {}".format(path.name))

    return failures, True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fetch", action="store_true", help="download PDFs first")
    ap.add_argument(
        "--year", type=int, action="append", help="report year (repeatable)"
    )
    ap.add_argument(
        "--organism", action="append", help="organism name (repeatable)"
    )
    ap.add_argument("--strict", action="store_true", help="fail on fixture mismatch")
    args = ap.parse_args(argv)

    years = args.year or BUILD_YEARS
    unknown = [y for y in years if y not in BUILD_YEARS]
    if unknown:
        ap.error(
            "year(s) {} are not built yet; this builder covers {}. The parser is "
            "verified against a hand-read of those editions only.".format(
                unknown, BUILD_YEARS
            )
        )

    organisms = args.organism or ORGANISMS
    unknown_organisms = [o for o in organisms if o not in SPECS]
    if unknown_organisms:
        ap.error(
            "unknown organism(s) {}; this builder covers {}. E. coli and "
            "S. aureus are the only organisms both networks report at species "
            "level.".format(unknown_organisms, ORGANISMS)
        )

    records, parsed, failed, extracted_date = build(
        fetch_first=args.fetch, years=years, organisms=organisms
    )
    if not records:
        print("No records extracted.")
        return 1

    failures, wrote = export(records, parsed, failed, extracted_date)
    if not wrote:
        return 1
    if failed:
        return 1
    if args.strict and failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
