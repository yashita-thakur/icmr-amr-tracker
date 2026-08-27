"""Orchestrate fetch -> parse -> validate -> export (spec section 5).

Usage:
    python -m src.build_dataset               # parse what is in data/raw/
    python -m src.build_dataset --fetch       # download first, then parse
    python -m src.build_dataset --strict      # exit non-zero on fixture failure

Exports to data/processed/:
    amr_trends.csv         one row per organism x antibiotic x year x report
    amr_trends.json        same, as a JSON array
    revisions.json         cross-report disagreements (spec section 2.1)
    extraction_report.json run metadata: what was parsed, from where, and how
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import sys

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from .parsers import enterobacterales as entero
from .parsers import nfgnb, staph
from .parsers.base import FIELDNAMES
from .parsers.trend_parser import parse_report as parse_trend
from .sources import ATTRIBUTION, PROCESSED_DIR, SOURCES
from .validate import check_fixtures, find_cross_report_revisions, internal_consistency

# Organism -> spec, in report order (Enterobacterales, non-fermenters, Staph).
SPECS = {}
for _mod in (entero, nfgnb, staph):
    SPECS.update(_mod.SPECS)

ORGANISMS = list(SPECS)


def build(fetch_first: bool = False, years=None, organisms=None):
    years = sorted(years or SOURCES, reverse=True)
    organisms = organisms or ORGANISMS
    extracted_date = _dt.date.today().isoformat()

    if fetch_first:
        from .fetch import fetch_one

        print("== fetch ==")
        for y in years:
            fetch_one(SOURCES[y])
        print()

    print("== parse ==")
    records = []
    parsed, failed = [], []
    for year in years:
        source = SOURCES[year]
        for organism in organisms:
            try:
                recs = parse_trend(source, SPECS[organism], extracted_date)
            except Exception as exc:  # noqa: BLE001 - collect, report, continue
                print("  [FAIL] {} {}: {}".format(year, organism, exc))
                failed.append(
                    {"report_year": year, "organism": organism, "error": str(exc)}
                )
                continue
            records.extend(recs)
            table = recs[0].source_table
            n_years = len({r.year for r in recs})
            n_abx = len({r.antibiotic for r in recs})
            print(
                "  [ok]   {} {:<24} {:<10} {:>3} rows  {} antibiotics x {} years".format(
                    year, organism, table, len(recs), n_abx, n_years
                )
            )
            parsed.append(
                {
                    "report_year": year,
                    "organism": organism,
                    "source_table": table,
                    "rows": len(recs),
                    "antibiotics": n_abx,
                    "years": sorted({r.year for r in recs}),
                }
            )
    return records, parsed, failed, extracted_date


def export(records, parsed, failed, extracted_date, revisions):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    rows = [r.to_dict() for r in records]
    rows.sort(
        key=lambda d: (
            d["organism"],
            d["antibiotic"],
            d["year"],
            d["source_report_year"],
        )
    )

    csv_path = PROCESSED_DIR / "amr_trends.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    json_path = PROCESSED_DIR / "amr_trends.json"
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2)

    rev_path = PROCESSED_DIR / "revisions.json"
    with open(rev_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "description": (
                    "Same (organism, antibiotic, year) reported with different "
                    "susceptibility percentages by different ICMR report "
                    "editions. This reflects revision/de-duplication in ICMR's "
                    "own publications, not an extraction error."
                ),
                "attribution": ATTRIBUTION,
                "generated": extracted_date,
                "count": len(revisions),
                "revisions": revisions,
            },
            fh,
            indent=2,
        )

    rep_path = PROCESSED_DIR / "extraction_report.json"
    with open(rep_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "generated": extracted_date,
                "attribution": ATTRIBUTION,
                "total_rows": len(rows),
                "sources": [
                    {
                        "report_year": s.report_year,
                        "edition": s.edition,
                        "url": s.url,
                        "sha256": s.sha256,
                    }
                    for s in sorted(
                        SOURCES.values(), key=lambda s: s.report_year, reverse=True
                    )
                ],
                "parsed": parsed,
                "failed": failed,
            },
            fh,
            indent=2,
        )

    return [csv_path, json_path, rev_path, rep_path]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fetch", action="store_true", help="download PDFs first")
    ap.add_argument("--year", type=int, action="append", help="report year (repeatable)")
    ap.add_argument("--strict", action="store_true", help="fail on fixture mismatch")
    args = ap.parse_args(argv)

    records, parsed, failed, extracted_date = build(
        fetch_first=args.fetch, years=args.year
    )
    if not records:
        print("\nNo records extracted. Aborting.")
        return 1

    print("\n== validate (spec section 4) ==")
    passes, failures = check_fixtures(records)
    for line in passes:
        print("  " + line)
    for line in failures:
        print("  " + line)
    print("  {} passed, {} failed".format(len(passes), len(failures)))

    mismatches = internal_consistency(records)
    if mismatches:
        print(
            "\n  {} record(s) where the printed % disagrees with n/N "
            "(flagged, not dropped):".format(len(mismatches))
        )
        for r in mismatches[:10]:
            print(
                "    {} {} {} ({} report): {}".format(
                    r.organism, r.antibiotic, r.year, r.source_report_year, r.flags
                )
            )

    revisions = find_cross_report_revisions(records)
    print("\n== cross-report revisions (spec section 2.1) ==")
    if not revisions:
        print("  none detected")
    else:
        print("  {} (organism, antibiotic, year) disagree between editions".format(
            len(revisions)
        ))
        for rev in revisions[:10]:
            print(
                "    [{}] {} {} {}".format(
                    rev["kind"], rev["organism"], rev["antibiotic"], rev["year"]
                )
            )
            print(
                "        susceptible_n {}  tested_n {}  pct {}".format(
                    rev["susceptible_n_by_report"],
                    rev["tested_n_by_report"],
                    rev["susceptible_pct_by_report"],
                )
            )

    print("\n== export ==")
    for p in export(records, parsed, failed, extracted_date, revisions):
        print("  wrote {}".format(p))
    print("\n{} rows total".format(len(records)))
    print(ATTRIBUTION)

    if args.strict and (failures or failed):
        print("\nSTRICT: failing because fixtures or parses did not all pass.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
