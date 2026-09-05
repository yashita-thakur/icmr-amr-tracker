"""V3 -- build the cross-network comparability matrix.

Usage:
    python -m src.build_comparability

Exports to data/processed/:
    comparability_matrix.json   one cell per organism x antibiotic x year,
                                recording which network reports it, on which
                                metric, from which specimen basis, and out of
                                which printed table

**This file carries no percentage and no count from either network, and that is
enforced rather than intended.** The two networks do not share a comparison
value: AMRSN publishes % susceptible, NARS-Net publishes % resistant, and AMRSN
publishes no % intermediate for either organism, so an AMRSN % resistant cannot
be computed and the two series can never be joined on one number. A matrix that
carried values would be exactly the join that must not exist -- so the matrix
joins on *keys* and stops there. `assert_carries_no_values` runs on the payload
before it is written and raises if a value-bearing field name or any float has
found its way in; `tests/test_comparability.py` runs the same assertion.

Unlike `build_dataset.py`, `build_rc_dataset.py` and `build_narsnet_dataset.py`,
this builder reads no PDFs. It is a second-order artefact derived from the two
already-extracted datasets, so it must be rebuilt after either of them changes.
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import sys

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from .sources import ATTRIBUTION, PROCESSED_DIR

# The two organisms both networks report at species level. Klebsiella,
# Pseudomonas and Acinetobacter are genus-level in every NARS-Net edition and
# species-level in AMRSN, so they are not comparable at all and are not in this
# matrix -- see docs/narsnet_v3_research.md A1.
ORGANISMS = ["Escherichia coli", "Staphylococcus aureus"]

YEARS = list(range(2017, 2025))

AMRSN = "amrsn"
NARSNET = "narsnet"

PERCENT_SUSCEPTIBLE = "percent_susceptible"
PERCENT_RESISTANT = "percent_resistant"

# Quoted from the table captions, checked in all three AMRSN editions (2022
# Table 3.6 / 6.4, 2023 Table 3.6 / 7.4, 2024 Table 2.6 / 6.4). The two
# organisms are NOT on the same basis: the E. coli caption excludes urine and
# faeces, the S. aureus caption states no exclusion at all. That asymmetry
# changes what a NARS-Net stratum can fairly be read beside, per organism, so
# it is carried per organism rather than flattened to one network-wide string.
AMRSN_SPECIMEN_BASIS = {
    "Escherichia coli": "all samples (except faeces and urine)",
    "Staphylococcus aureus": "all samples",
}

COVERAGE_BOTH = "both"
COVERAGE_NARSNET_ONLY = "narsnet_only"
COVERAGE_AMRSN_ONLY = "amrsn_only"
COVERAGE_NEITHER = "neither"

COVERAGE_STATES = [
    COVERAGE_BOTH,
    COVERAGE_NARSNET_ONLY,
    COVERAGE_AMRSN_ONLY,
    COVERAGE_NEITHER,
]

# Every value-bearing field name in either row schema. None of these may appear
# as a key anywhere in the exported payload, at any depth.
VALUE_FIELDS = frozenset(
    {
        "susceptible_n",
        "susceptible_pct",
        "resistant_n",
        "resistant_pct",
        "tested_n",
        "reported_pct",
        "computed_pct",
        "ci_low",
        "ci_high",
    }
)


class ValueLeakError(AssertionError):
    """A surveillance value reached the comparability matrix."""


def assert_carries_no_values(payload, path="payload"):
    """Raise if a value-bearing field name or any float is in the payload.

    Two separate checks, because they fail differently. A forbidden *key* is
    someone copying a field across from one of the row schemas. A *float* is
    someone computing something -- every legitimate number here is a year or a
    tally of cells, and both are integers. Neither is a style rule: a matrix
    that carried a percentage would let a reader do the join this project
    exists to prevent.
    """
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in VALUE_FIELDS:
                raise ValueLeakError(
                    "{}.{}: {!r} is a value-bearing field and must not appear "
                    "in the comparability matrix. The matrix joins the two "
                    "networks on keys only; they share no comparison "
                    "value.".format(path, key, key)
                )
            assert_carries_no_values(value, "{}.{}".format(path, key))
    elif isinstance(payload, list):
        for i, value in enumerate(payload):
            assert_carries_no_values(value, "{}[{}]".format(path, i))
    elif isinstance(payload, float):
        raise ValueLeakError(
            "{}: {!r} is a float. Every number in the comparability matrix is "
            "a year or a count of cells, both integers; a float here means a "
            "percentage or a derived figure has leaked in.".format(path, payload)
        )


def _read_csv(name):
    path = PROCESSED_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            "{} not found. The comparability matrix is derived from the two "
            "extracted datasets -- build them first.".format(path)
        )
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_amrsn_rows():
    return [r for r in _read_csv("amr_trends.csv") if r["organism"] in ORGANISMS]


def load_narsnet_rows():
    return [r for r in _read_csv("narsnet_trends.csv") if r["organism"] in ORGANISMS]


def _source(report_year, table):
    return {"report_year": int(report_year), "table": table}


def _sorted_sources(sources):
    unique = {(s["report_year"], s["table"]): s for s in sources}
    return [unique[k] for k in sorted(unique)]


def amrsn_coverage(rows):
    """(organism, antibiotic, year) -> what AMRSN prints for it.

    A calendar year is carried by up to three editions, each with its own
    retrospective table, so `sources` is a list. That the same year is printed
    three times is what makes AMRSN revision detection possible at all, and is
    worth keeping visible here rather than collapsing to the latest edition.
    """
    out = {}
    for row in rows:
        key = (row["organism"], row["antibiotic"], int(row["year"]))
        entry = out.setdefault(key, {"sources": []})
        entry["sources"].append(
            _source(row["source_report_year"], row["source_table"])
        )
    return {
        key: {
            "metric": PERCENT_SUSCEPTIBLE,
            "specimen_basis": AMRSN_SPECIMEN_BASIS[key[0]],
            "sources": _sorted_sources(entry["sources"]),
        }
        for key, entry in out.items()
    }


def narsnet_coverage(rows):
    """(organism, antibiotic, year) -> what NARS-Net prints for it.

    `specimen_basis` is the set of specimen columns *this drug* is reported in
    that year, not the edition's full column set: a drug can be greyed out in
    some columns and printed in others (2019 E. coli nitrofurantoin is urine
    only). Composite columns keep every constituent in their label, because
    their membership is not the same across editions.
    """
    out = {}
    for row in rows:
        key = (row["organism"], row["antibiotic"], int(row["year"]))
        entry = out.setdefault(key, {"specimens": set(), "sources": []})
        entry["specimens"].add(row["specimen"])
        entry["sources"].append(
            _source(row["source_report_year"], row["source_table"])
        )
    return {
        key: {
            "metric": PERCENT_RESISTANT,
            "specimen_basis": sorted(entry["specimens"]),
            "sources": _sorted_sources(entry["sources"]),
        }
        for key, entry in out.items()
    }


def _cell(organism, antibiotic, year, amrsn_entry, narsnet_entry):
    if amrsn_entry and narsnet_entry:
        coverage = COVERAGE_BOTH
    elif narsnet_entry:
        coverage = COVERAGE_NARSNET_ONLY
    elif amrsn_entry:
        coverage = COVERAGE_AMRSN_ONLY
    else:
        coverage = COVERAGE_NEITHER
    return {
        "organism": organism,
        "antibiotic": antibiotic,
        "year": year,
        "coverage": coverage,
        AMRSN: dict(amrsn_entry) if amrsn_entry else None,
        NARSNET: dict(narsnet_entry) if narsnet_entry else None,
    }


def build_matrix(amrsn, narsnet, organisms=None, years=None):
    """The full rectangular matrix, one cell per organism x drug x year.

    Rectangular on purpose. A cell neither network reports is a real statement
    about the two panels and is what the blank squares in the figure are; a
    sparse file would leave the reader to work out whether a missing key means
    "not reported" or "not extracted".
    """
    organisms = organisms or ORGANISMS
    years = years or YEARS
    cells = []
    for organism in organisms:
        drugs = sorted(
            {a for (o, a, _y) in amrsn if o == organism}
            | {a for (o, a, _y) in narsnet if o == organism}
        )
        for antibiotic in drugs:
            for year in years:
                key = (organism, antibiotic, year)
                cells.append(
                    _cell(organism, antibiotic, year, amrsn.get(key), narsnet.get(key))
                )
    return cells


def summarise(cells, organisms=None, years=None):
    organisms = organisms or ORGANISMS
    years = years or YEARS
    per_organism = []
    for organism in organisms:
        own = [c for c in cells if c["organism"] == organism]
        drugs = sorted({c["antibiotic"] for c in own})
        counts = {state: 0 for state in COVERAGE_STATES}
        for cell in own:
            counts[cell["coverage"]] += 1
        # Membership over the whole series, not per year: a drug counts as
        # reported by a network if that network prints it in any year at all.
        # This is the panel-overlap question, and it is not the same as the
        # cell counts above -- ceftazidime is reported by both networks and so
        # is "shared", but only one of its eight E. coli cells is a "both".
        by_amrsn = {c["antibiotic"] for c in own if c[AMRSN] is not None}
        by_narsnet = {c["antibiotic"] for c in own if c[NARSNET] is not None}
        per_organism.append(
            {
                "organism": organism,
                "antibiotics": drugs,
                "antibiotic_count": len(drugs),
                "years": list(years),
                "cells": len(own),
                "coverage_counts": counts,
                "antibiotics_both_networks_report": sorted(by_amrsn & by_narsnet),
                "antibiotics_narsnet_only": sorted(by_narsnet - by_amrsn),
                "antibiotics_amrsn_only": sorted(by_amrsn - by_narsnet),
            }
        )
    totals = {state: 0 for state in COVERAGE_STATES}
    for cell in cells:
        totals[cell["coverage"]] += 1
    return {
        "cells": len(cells),
        "coverage_counts": totals,
        "by_organism": per_organism,
    }


DESCRIPTION = (
    "Which of the two networks reports each organism x antibiotic x year, on "
    "which metric, from which specimen basis, and out of which printed table. "
    "THE MATRIX CARRIES NO PERCENTAGE AND NO COUNT FROM EITHER NETWORK, and "
    "that is enforced by assert_carries_no_values() at build time and again in "
    "tests/test_comparability.py, not merely intended. The two networks share "
    "no comparison value: AMRSN publishes percent susceptible, NARS-Net "
    "publishes percent resistant, and AMRSN publishes no percent intermediate "
    "for E. coli or S. aureus, so an AMRSN percent resistant cannot be "
    "computed. A 'both' cell therefore means both networks report that "
    "combination, NEVER that the two figures are comparable with each other. "
    "Read the two datasets as parallel series and take each value from its own "
    "file: amr_trends.csv for AMRSN, narsnet_trends.csv for NARS-Net."
)

SPECIMEN_NOTE = (
    "The specimen bases are not equivalent and are not equivalent in the same "
    "way for the two organisms. AMRSN prints ONE pooled column per year with no "
    "specimen breakdown in these trend tables, captioned 'all samples (except "
    "faeces and urine)' for E. coli but 'all samples' -- no exclusion stated -- "
    "for S. aureus. NARS-Net prints a separate column per specimen and, from "
    "the 2021 edition, no pooled column at all, so a single national NARS-Net "
    "percentage across specimens is not printed anywhere and is not "
    "reconstructed here. Where a NARS-Net specimen_basis entry contains '+', "
    "the source column is a composite of those strata, and composite "
    "membership changes between editions: no post-2021 column has the same "
    "membership as any pre-2021 one."
)

SOURCES_NOTE = (
    "AMRSN carries each calendar year in up to three editions' retrospective "
    "tables, so its 'sources' list usually holds more than one entry; that "
    "repetition is what makes cross-edition revision detection possible, and "
    "revisions.json records the 17 found. Each NARS-Net edition reports its own "
    "period only, so its 'sources' list always holds exactly one entry and "
    "narsnet_revisions.json is empty by design."
)


def export(cells, summary, generated=None, path=None):
    generated = generated or _dt.date.today().isoformat()
    path = path or PROCESSED_DIR / "comparability_matrix.json"
    payload = {
        "description": DESCRIPTION,
        "specimen_basis_note": SPECIMEN_NOTE,
        "sources_note": SOURCES_NOTE,
        "attribution": ATTRIBUTION,
        "generated": generated,
        "metrics": {AMRSN: PERCENT_SUSCEPTIBLE, NARSNET: PERCENT_RESISTANT},
        "coverage_states": COVERAGE_STATES,
        "summary": summary,
        "matrix": cells,
    }
    assert_carries_no_values(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return path


def main(argv=None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)

    print("== load ==")
    amrsn_rows = load_amrsn_rows()
    narsnet_rows = load_narsnet_rows()
    print("  {:>5} AMRSN rows (E. coli, S. aureus)".format(len(amrsn_rows)))
    print("  {:>5} NARS-Net rows".format(len(narsnet_rows)))

    amrsn = amrsn_coverage(amrsn_rows)
    narsnet = narsnet_coverage(narsnet_rows)
    cells = build_matrix(amrsn, narsnet)
    summary = summarise(cells)

    print("\n== matrix ==")
    for entry in summary["by_organism"]:
        counts = entry["coverage_counts"]
        print(
            "  {:<24} {:>2} drugs x {} years = {:>3} cells  "
            "both={:<3} narsnet_only={:<3} amrsn_only={:<3} neither={}".format(
                entry["organism"],
                entry["antibiotic_count"],
                len(entry["years"]),
                entry["cells"],
                counts[COVERAGE_BOTH],
                counts[COVERAGE_NARSNET_ONLY],
                counts[COVERAGE_AMRSN_ONLY],
                counts[COVERAGE_NEITHER],
            )
        )
    totals = summary["coverage_counts"]
    print(
        "  {:<24} {:>21} {:>3} cells  both={:<3} narsnet_only={:<3} "
        "amrsn_only={:<3} neither={}".format(
            "TOTAL",
            "",
            summary["cells"],
            totals[COVERAGE_BOTH],
            totals[COVERAGE_NARSNET_ONLY],
            totals[COVERAGE_AMRSN_ONLY],
            totals[COVERAGE_NEITHER],
        )
    )

    print("\n== export ==")
    print("  wrote {}".format(export(cells, summary)))
    print("\n{}".format(ATTRIBUTION))
    return 0


if __name__ == "__main__":
    sys.exit(main())
