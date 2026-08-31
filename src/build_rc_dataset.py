"""V2 -- build the Regional Centre (RC) breakdown dataset.

Usage:
    python -m src.build_rc_dataset            # parse what is in data/raw/
    python -m src.build_rc_dataset --fetch    # download first, then parse
    python -m src.build_rc_dataset --strict   # exit non-zero on fixture failure

Companion to `build_dataset.py` (V1, national). The two are kept separate on
purpose: the RC-wise tables are single-year cross-sections with a different
schema and a much narrower organism coverage, and merging them into
`amr_trends.csv` would blur that. See the README section "Regional Centre
tables are a single-year cross-section".

Exports to data/processed/:
    amr_rc_trends.csv        one row per organism x RC x antibiotic x edition
    amr_rc_trends.json       same, as a JSON array
    rc_panel.json            per organism: the RC set each edition printed, and
                             what was added / dropped versus the earliest edition
    rc_revisions.json        cross-edition differences -- structurally near
                             empty (single-year cross-sections); see its own
                             "note" field
    rc_extraction_report.json  run metadata: sources, hashes, what parsed
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import sys

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from .parsers.rc_parser import (
    EXPECTED_EDITIONS,
    RC_FIELDNAMES,
    SPECS,
    parse_rc_report,
)
from .rc_validate import (
    apply_rc_panel_flags,
    check_rc_fixtures,
    find_rc_cross_report_revisions,
    rc_internal_consistency,
    rc_panel_by_edition,
)
from .sources import ATTRIBUTION, PROCESSED_DIR, SOURCES

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

    print("== parse (RC-wise AMS tables) ==")
    records = []
    parsed, failed, skipped = [], [], []
    for year in years:
        source = SOURCES[year]
        for organism in organisms:
            expected = year in EXPECTED_EDITIONS.get(organism, set())
            try:
                recs = parse_rc_report(source, SPECS[organism], extracted_date)
            except Exception as exc:  # noqa: BLE001 - collect, report, continue
                if not expected:
                    print(
                        "  [skip]  {} {:<24} no RC-wise table in this edition "
                        "(expected)".format(year, organism)
                    )
                    skipped.append({"report_year": year, "organism": organism})
                else:
                    print("  [FAIL]  {} {}: {}".format(year, organism, exc))
                    failed.append(
                        {"report_year": year, "organism": organism, "error": str(exc)}
                    )
                continue
            records.extend(recs)
            table = recs[0].source_table
            rcs = {r.regional_centre for r in recs}
            abx = {r.antibiotic for r in recs}
            print(
                "  [ok]    {} {:<24} {:<11} {:>4} rows  {} RCs x {} antibiotics".format(
                    year, organism, table, len(recs), len(rcs), len(abx)
                )
            )
            parsed.append(
                {
                    "report_year": year,
                    "organism": organism,
                    "source_table": table,
                    "rows": len(recs),
                    "regional_centres": sorted(rcs, key=_rc_num),
                    "antibiotics": sorted(abx),
                }
            )

    return records, parsed, failed, skipped, extracted_date


def _rc_num(label: str) -> int:
    d = "".join(ch for ch in label if ch.isdigit())
    return int(d) if d else 0


def export(records, parsed, failed, skipped, extracted_date, panel_changes, revisions):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    rows = [r.to_dict() for r in records]
    rows.sort(
        key=lambda d: (
            d["organism"],
            _rc_num(d["regional_centre"]),
            d["antibiotic"],
            d["source_report_year"],
        )
    )

    csv_path = PROCESSED_DIR / "amr_rc_trends.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=RC_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    json_path = PROCESSED_DIR / "amr_rc_trends.json"
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2)

    panel_path = PROCESSED_DIR / "rc_panel.json"
    with open(panel_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "description": (
                    "Regional Centre codes (RC1..RCn) are de-identified in the "
                    "reports, and the code-to-institution mapping is not part of "
                    "the published tables. Treat them as edition-scoped: an RC "
                    "that appears in two editions need not be the same "
                    "laboratory, and a change in numbering between editions "
                    "would not be signposted. This file records, per organism, "
                    "the RC set each edition printed and how it differs from "
                    "that organism's earliest edition. Every data row from an "
                    "edition listed under 'changes' also carries an "
                    "rc_panel_changed(...) flag."
                ),
                "attribution": ATTRIBUTION,
                "generated": extracted_date,
                "panel_by_edition": rc_panel_by_edition(records),
                "changes": panel_changes,
            },
            fh,
            indent=2,
        )

    rev_path = PROCESSED_DIR / "rc_revisions.json"
    with open(rev_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "note": (
                    "The RC-wise AMS tables are single-year cross-sections: each "
                    "edition reports its own year only, with no retrospective "
                    "trend axis. No (organism, regional_centre, antibiotic, year) "
                    "key is therefore covered by more than one edition, so "
                    "cross-edition revision detection has almost nothing to "
                    "compare. An empty or near-empty result here is BY DESIGN, "
                    "not a sign the check failed -- contrast "
                    "revisions.json (V1), where every year is covered up to "
                    "three times. See the README section 'Regional Centre "
                    "tables are a single-year cross-section'."
                ),
                "attribution": ATTRIBUTION,
                "generated": extracted_date,
                "count": len(revisions),
                "revisions": revisions,
            },
            fh,
            indent=2,
        )

    rep_path = PROCESSED_DIR / "rc_extraction_report.json"
    with open(rep_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "generated": extracted_date,
                "attribution": ATTRIBUTION,
                "total_rows": len(rows),
                "coverage_note": (
                    "Only Escherichia coli, Klebsiella pneumoniae and "
                    "Staphylococcus aureus have an RC-wise AMS table for the "
                    "non-urine population. E. coli / K. pneumoniae have one only "
                    "from the 2023 edition on; the 2022 edition breaks them down "
                    "by RC for urine isolates only, which is out of scope. "
                    "A. baumannii, P. aeruginosa and MRSA have no RC-wise AMS "
                    "table in any edition."
                ),
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
                "skipped_no_table_this_edition": skipped,
                "failed": failed,
            },
            fh,
            indent=2,
        )

    return [csv_path, json_path, panel_path, rev_path, rep_path]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fetch", action="store_true", help="download PDFs first")
    ap.add_argument("--year", type=int, action="append", help="report year (repeatable)")
    ap.add_argument("--strict", action="store_true", help="fail on fixture mismatch")
    args = ap.parse_args(argv)

    records, parsed, failed, skipped, extracted_date = build(
        fetch_first=args.fetch, years=args.year
    )
    if not records:
        print("\nNo RC records extracted. Aborting.")
        return 1

    # Attach the panel-changed flag before anything reads flags off the records.
    print("\n== RC panel change detection ==")
    panel_changes = apply_rc_panel_flags(records)
    if not panel_changes:
        print("  RC panel identical across editions for every organism")
    for c in panel_changes:
        print(
            "  {} {}: vs {} baseline -- added {} dropped {}".format(
                c["organism"],
                c["edition"],
                c["baseline_edition"],
                c["added"] or "[]",
                c["dropped"] or "[]",
            )
        )

    print("\n== validate ==")
    passes, failures = check_rc_fixtures(records)
    for line in passes:
        print("  " + line)
    for line in failures:
        print("  " + line)
    print("  {} passed, {} failed".format(len(passes), len(failures)))

    mismatches = rc_internal_consistency(records)
    if mismatches:
        print(
            "\n  {} record(s) where the printed % and n/N do not fully "
            "reconcile (flagged, not dropped):".format(len(mismatches))
        )
        for r in mismatches[:10]:
            print(
                "    {} {} {} ({} edition): {}".format(
                    r.organism, r.regional_centre, r.antibiotic,
                    r.source_report_year, r.flags,
                )
            )

    revisions = find_rc_cross_report_revisions(records)
    print("\n== cross-edition revisions ==")
    print(
        "  {} found (expected ~0: single-year cross-sections -- see "
        "rc_revisions.json)".format(len(revisions))
    )

    print("\n== export ==")
    for p in export(
        records, parsed, failed, skipped, extracted_date, panel_changes, revisions
    ):
        print("  wrote {}".format(p))
    print("\n{} RC rows total".format(len(records)))
    print(ATTRIBUTION)

    if args.strict and (failures or failed):
        print("\nSTRICT: failing because fixtures or parses did not all pass.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
