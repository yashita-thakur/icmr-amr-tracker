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

Scope is all eight editions, 2017-2024, E. coli and S. aureus. The series
changes what it prints twice inside that window, and the checks follow it:
2019-2021 print a numerator, so each cell is checked against its own printed
percentage (all but the fifteen cells declared in `CORRUPT_NUMERATORS`);
2022-2024 print a 95% confidence interval instead, so each cell is checked
against its own interval. The 2017 and 2018 editions print neither, so no check
inside a cell reaches them at all; what does stand behind those rows is set out
in the parser's module docstring and repeated in the `scope` field of
narsnet_extraction_report.json, where a reader of the data will meet it.

Whether a check actually ran on a given cell is on the row itself, as the flag
`no_internal_check_possible`, and not inferable from `reconcilable`, which
answers a different question -- see the parser's module docstring. It is raised
on 125 cells across four editions.
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
    summarise_ci_checks,
    summarise_composite_sums,
    summarise_corrupt_numerators,
    summarise_unchecked_cells,
)
from .parsers.narsnet_parser import (
    NARSNET_FIELDNAMES,
    SPECS,
    parse_narsnet_report,
)
from .sources import ATTRIBUTION, NARSNET_SOURCES, PROCESSED_DIR

# Editions this builder covers. Kept here rather than derived from
# NARSNET_SOURCES, which holds the same eight: the registry records what can be
# fetched, this records what has been verified against a hand-read of the page.
# The two now agree, and the separation is still worth keeping -- a ninth
# edition would be fetchable the day it is registered and buildable only once
# someone had read it.
BUILD_YEARS = [2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017]

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

    corrupt = summarise_corrupt_numerators(records)
    corrupt_cells = sum(c["cells"] for c in corrupt)
    print(
        "  corrupt numerators   {} cell(s) in {} declared block(s)".format(
            corrupt_cells, len(corrupt)
        )
    )
    for c in corrupt:
        scope = c["scope"] if isinstance(c["scope"], str) else ", ".join(c["scope"])
        print(
            "    {} {} / {}: {} ({} cell(s), {} agree with their own printed %R)".format(
                c["source_report_year"], c["organism"], c["specimen"], scope,
                c["cells"], c["cells_agreeing_with_their_printed_pct"],
            )
        )
        if not c["cells"]:
            print(
                "      [WARN] this declaration matched no rows in this build"
            )

    ci_findings = summarise_ci_checks(records)
    print(
        "  printed %R vs its CI  {} row(s) sit outside their own printed "
        "interval".format(len(ci_findings))
    )
    for c in ci_findings:
        print(
            "    {} {} {} / {}: {}% against {}-{} ({} away from the nearer "
            "bound{})".format(
                c["source_report_year"], c["organism"], c["antibiotic"],
                c["specimen"], c["reported_pct"], c["ci_low"], c["ci_high"],
                c["distance_to_nearer_bound"],
                "; within the precision the percentage is printed to"
                if c["within_the_printed_precision"]
                else "; bounds printed in reverse order"
                if c["bounds_inverted"]
                else "",
            )
        )

    unchecked = summarise_unchecked_cells(records)
    print(
        "  no check reached    {} cell(s), in {} edition(s)".format(
            unchecked["count"], len(unchecked["by_edition"])
        )
    )
    for year, entry in unchecked["by_edition"].items():
        print(
            "    {}: {} cell(s) -- {}".format(
                year, entry["cells"],
                "; ".join(
                    "{} ({})".format(reason, n)
                    for reason, n in sorted(entry["reasons"].items())
                ),
            )
        )

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
                    "printed column against one that is no longer printed. The "
                    "2021 edition moves both axes at once: the drug panels grow "
                    "from 9 to 17 for E. coli and 8 to 9 for S. aureus, and the "
                    "pooled and PA+OSBF columns give way to pus_aspirate and "
                    "osbf reported separately, so no 2021 specimen column has "
                    "the same membership as any 2020 one. "
                    "NOTHING IN THE SERIES APPEARS, DISAPPEARS AND RETURNS. "
                    "Checked across all eight editions, on both axes and both "
                    "organisms: each of the 41 drugs and specimen columns is "
                    "printed over one unbroken run of editions, so the changes "
                    "below, which compare consecutive editions only, describe "
                    "the whole of what moves. A drug or column absent from an "
                    "edition between two that print it would not be visible "
                    "there, and there is none. Two drugs run for a single "
                    "edition -- E. coli ceftazidime in 2017 and S. aureus "
                    "vancomycin in 2018 -- and neither returns."
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
                    "All eight editions, 2017 to 2024, E. coli and S. aureus. "
                    "What the series prints changes twice inside that window "
                    "and the checks follow it. 2019-2021 print Number Tested, "
                    "Number Resistant and a percentage, so every cell is "
                    "checked against its own printed percentage, except the "
                    "fifteen listed under corrupt_numerators where the printed "
                    "figure is not that cell's numerator. 2022-2024 print "
                    "Number Tested, a percentage and a 95% confidence interval "
                    "and no numerator at all, so numerator_status is "
                    "not_printed_in_source and reconcilable is false on every "
                    "one of those rows, and the check that applies instead is "
                    "the percentage against its own interval, under "
                    "printed_pct_vs_printed_ci."
                ),
                "editions_no_check_reaches": (
                    "READ THIS BEFORE USING A 2017 OR 2018 FIGURE. Those two "
                    "editions print a denominator and a percentage and nothing "
                    "else. There is no numerator for the percentage to be "
                    "reconciled against and no interval for it to fall outside "
                    "of, so NO CHECK INSIDE A CELL APPLIES TO THEM: all 108 "
                    "of those rows carry the flag no_internal_check_possible, "
                    "numerator_status is not_printed_in_source, and neither "
                    "printed_pct_vs_printed_counts nor "
                    "printed_pct_vs_printed_ci can ever contain one. Read the "
                    "flag rather than reconcilable, which answers a different "
                    "question and is false on the 2022-2024 rows too, and those "
                    "ARE checked -- see cells_no_internal_check_reaches. What "
                    "stands behind them instead is, first, the chapter prose: "
                    "both editions state specimen-stratified percentages, "
                    "twenty-one in all, and every one is pinned as a fixture "
                    "rather than a sample being taken. Second, the 2018 "
                    "chapter restating 2017 -- it gives the previous year's "
                    "S. aureus blood cefoxitin as 57% and its E. coli blood "
                    "ertapenem and imipenem as 37% and 25%, against a 2017 "
                    "table printing 57.1, 36.7 and 25.2. Third, for every "
                    "other cell, the column geometry and nothing else. A "
                    "figure from those two editions that no fixture covers is "
                    "the extraction's reading of the page, with nothing "
                    "printed on the page able to contradict it."
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
                "corrupt_numerators": {
                    "description": (
                        "Cells whose printed Number Resistant is not that "
                        "cell's numerator. They are carried exactly as printed "
                        "and flagged numerator_corrupt_in_source; "
                        "numerator_status is corrupt_in_source, reconcilable is "
                        "false, and no computed_pct is derived from them. "
                        "Nothing is corrected and nothing is dropped. This is a "
                        "different finding from "
                        "printed_pct_vs_printed_counts below, where the "
                        "numerator IS the cell's own figure and disagrees with "
                        "the percentage beside it. Which cells these are is "
                        "declared from a hand-read of the printed page rather "
                        "than inferred from the size of the disagreement. "
                        "cells_agreeing_with_their_printed_pct counts the cells "
                        "inside a declared block whose printed numerator does "
                        "nonetheless agree with the percentage printed beside "
                        "it; they are reported here rather than exempted, "
                        "because where the unit of a printing defect is the "
                        "sub-column, which values came to rest on their own row "
                        "is not something the printed table lets a reader "
                        "establish."
                    ),
                    "count": len(corrupt),
                    "cells": corrupt_cells,
                    "blocks": corrupt,
                },
                "cells_no_internal_check_reaches": {
                    "description": (
                        "Cells flagged no_internal_check_possible: cells where "
                        "neither check had two printed figures to compare, so "
                        "neither ran. RECONCILABLE DOES NOT ANSWER THIS "
                        "QUESTION and must not be read as though it did. It "
                        "says whether the printed numerator can be trusted as "
                        "that cell's numerator, which is a different fact: it "
                        "is false on every 2022-2024 row, and those rows ARE "
                        "checked, against their own interval; and it is true on "
                        "one 2021 row that is checked against nothing, because "
                        "the percentage column is blank there. The flag is "
                        "derived per cell from what the cell prints, never from "
                        "its edition. It lands on all 108 rows of 2017 and "
                        "2018, which print no numerator and no interval; on the "
                        "fifteen 2021 cells whose numerator is corrupt in "
                        "source, which leaves the percentage nothing to "
                        "disagree with; and on two cells that print no "
                        "percentage at all. by_edition gives the shape; rows "
                        "names the ones outside 2017 and 2018, which are the "
                        "ones a reader could not predict from the edition."
                    ),
                    "count": unchecked["count"],
                    "by_edition": unchecked["by_edition"],
                    "rows_outside_2017_2018": unchecked["rows"],
                },
                "printed_pct_vs_printed_ci": {
                    "description": (
                        "Cells whose printed percentage lies outside its own "
                        "printed 95% confidence interval. This is the check the "
                        "2022-2024 editions can support: they print no "
                        "numerator, so there is nothing to reconcile a "
                        "percentage against, but a percentage and an interval "
                        "are two printed statements about one quantity and can "
                        "disagree without a third figure. Bounds are used "
                        "exactly as printed and are not put back in order. "
                        "distance_to_nearer_bound and "
                        "within_the_printed_precision are reported so the size "
                        "can be judged rather than assumed: a percentage "
                        "printed to whole numbers beside an interval printed to "
                        "one decimal can fall a tenth outside an interval that "
                        "in fact contains it, which is a difference between how "
                        "two columns are rounded, and is not the same finding "
                        "as an interval whose upper bound is printed below its "
                        "lower. All rows are carried exactly as printed and "
                        "flagged; nothing is corrected."
                    ),
                    "count": len(ci_findings),
                    "rows": ci_findings,
                },
                "printed_pct_vs_printed_counts": {
                    "description": (
                        "Cells whose printed percentage does not follow from "
                        "their own printed counts, allowing half the printed "
                        "precision for rounding. All are carried exactly as "
                        "printed and flagged; nothing is corrected. Cells whose "
                        "numerator is corrupt in source cannot appear here: "
                        "there is no numerator of their own for the percentage "
                        "to disagree with."
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
