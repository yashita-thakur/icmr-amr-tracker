"""V3 fixture validation and cross-column checks for the NARS-Net tables.

Fixtures follow the same convention as `validate.py`: provenance in `note`,
with "narrative" fixtures valued more highly than "table" ones because the
chapter prose is written independently of the table it describes, so agreement
between them is corroboration rather than a tautology. The NARS-Net chapters are
unusually generous here -- the 2019, 2020 and 2021 editions state two dozen
specimen-stratified percentages in prose, including the stratum each one belongs
to. That pays for itself in the 2021 E. coli table, where the chapter states the
Blood percentages for ciprofloxacin, TMP/SMX and piperacillin-tazobactam and the
Blood numerator sub-column beside them is not usable: the prose corroborates the
printed percentage from outside the table.

Three checks that `parsers/narsnet_parser.py` cannot make on its own:

* `find_degenerate_composite_disagreements` -- the cross-column check. Some
  drugs are reported for one specimen only, with the other blocks greyed out. A
  composite column then covers exactly one reported stratum, which makes the two
  columns two renderings of the SAME isolates. They must print the same counts.
  In the 2019 E. coli table they do not: nitrofurantoin is urine-only, both
  columns print a denominator of 16,741, and the numerators are 2,026 and 2,042.
  Nothing inside a single cell can see this.

* `summarise_composite_sums` -- descriptive only, deliberately NOT a flag. Where
  a composite column has a full partition among the other columns, its counts
  can be compared against their sum. Doing so across 2019 and 2020 shows the
  difference is systematic rather than exceptional: in 2019 every pooled
  denominator equals its partition sum exactly while no pooled numerator does
  (E. coli ciprofloxacin is +41), and in 2020 neither does. Flagging each row
  would mark almost every composite row in the dataset and bury the one finding
  that is genuinely anomalous. The measured differences are reported instead, so
  a reader can see the size of the effect and judge it.

* `summarise_corrupt_numerators` -- descriptive only, like the one above. The
  parser has already acted on `CORRUPT_NUMERATORS`; what this adds is the count
  of cells inside a declared block whose printed numerator does nonetheless
  agree with the percentage printed beside it. There are two, both in the 2021
  E. coli Blood sub-column. They are counted here rather than exempted there,
  so the judgement that the sub-column is the unit of the defect stays visible
  and can be argued with.

The first two are kept apart because they are different claims. A degenerate
composite disagreeing with its single stratum is an internal contradiction in
the printed table. A composite disagreeing with a sum of strata is expected: the
columns are separately de-duplicated and separately computed, and the reports do
not state that a pooled column is the arithmetic sum of the ones beside it.
"""

from __future__ import annotations

from dataclasses import dataclass

from .parsers.narsnet_parser import (
    CORRUPT_NUMERATORS,
    NUMERATOR_CORRUPT,
    is_composite,
    pct_tolerance,
)

# --- fixtures ---------------------------------------------------------------


@dataclass(frozen=True)
class NarsNetFixture:
    organism: str
    antibiotic: str
    specimen: str
    year: int
    expected_pct: float
    note: str
    expected_tested_n: int | None = None
    expected_resistant_n: int | None = None
    tolerance: float = 0.1

    @property
    def label(self) -> str:
        return "{} / {} / {} / {}".format(
            self.organism, self.antibiotic, self.specimen, self.year
        )


BLOOD = "blood"
URINE = "urine"
PUS_ASPIRATE = "pus_aspirate"
OSBF = "osbf"
PA_OSBF = "pus_aspirate+osbf"
BLOOD_PA_OSBF = "blood+pus_aspirate+osbf"
ALL_FOUR = "blood+urine+pus_aspirate+osbf"

EC = "Escherichia coli"
SA = "Staphylococcus aureus"

NARSNET_FIXTURES: list[NarsNetFixture] = [
    # --- 2019 E. coli, Ch.2 narrative (p29 [19]) ----------------------------
    # "E. coli isolated from blood showed 82% resistance to cefotaxime and 63%
    #  to cefepime whereas urine isolates show higher level of resistance to
    #  cefepime (66%) than to cefotaxime (77%)."
    # The prose gives percentages only. The counts below are the Table 6 cell,
    # hand-read off p29 -- a mixed-provenance fixture, so the percentage and the
    # counts corroborate each other rather than both coming from one rendering.
    NarsNetFixture(EC, "cefotaxime", BLOOD, 2019, 82.0,
                   "narrative (%R); table 6 cell, p29 (counts)",
                   expected_tested_n=1030, expected_resistant_n=841),
    NarsNetFixture(EC, "cefepime", BLOOD, 2019, 63.0, "narrative"),
    NarsNetFixture(EC, "cefepime", URINE, 2019, 66.0, "narrative"),
    NarsNetFixture(EC, "cefotaxime", URINE, 2019, 77.0, "narrative"),
    # "Resistance to imipenem is found to be 33% in E. coli blood isolates
    #  which is higher than that observed in urine isolates (32%)."
    NarsNetFixture(EC, "imipenem", BLOOD, 2019, 33.0, "narrative"),
    NarsNetFixture(EC, "imipenem", URINE, 2019, 32.0, "narrative"),

    # --- 2019 S. aureus, Ch.1 narrative (p23 [13]) --------------------------
    # "overall resistance to cefoxitin (surrogate marker for mecA-mediated
    #  oxacillin resistance) is 59%" -- stated of the 13,290 pooled isolates.
    # Percentage from the prose; counts from the Table 4 cell, hand-read off p24.
    NarsNetFixture(SA, "cefoxitin", BLOOD_PA_OSBF, 2019, 59.0,
                   "narrative (%R); table 4 cell, p24 (counts)",
                   expected_tested_n=11855, expected_resistant_n=6994),
    # "Of the S. aureus isolated from blood, 66% are MRSA."
    NarsNetFixture(SA, "cefoxitin", BLOOD, 2019, 66.0, "narrative"),
    # "Ciprofloxacin resistance is observed in 73% of S. aureus isolates from
    #  aspirated pus and OSBF and in 56% of S. aureus isolates from blood."
    NarsNetFixture(SA, "ciprofloxacin", PA_OSBF, 2019, 73.0, "narrative"),
    NarsNetFixture(SA, "ciprofloxacin", BLOOD, 2019, 56.0, "narrative"),
    # "Resistance to gentamicin is observed in 23% of S. aureus isolates."
    NarsNetFixture(SA, "gentamicin", BLOOD_PA_OSBF, 2019, 23.0, "narrative"),
    # "Linezolid resistance is observed in 1% of S. aureus isolates." The table
    # prints 0.9; the prose rounds. Tolerance widened for that one reason.
    NarsNetFixture(SA, "linezolid", BLOOD_PA_OSBF, 2019, 0.9,
                   "table 4 cell, p24 (narrative rounds the same figure to 1%)",
                   expected_tested_n=12314, expected_resistant_n=111),

    # --- 2020 S. aureus, Ch.1 narrative (p25 [21]) --------------------------
    # "Methicillin resistance is highest among S. aureus isolated from blood
    #  cultures that is 64%, followed by 52% in isolates from PA+OSBF."
    NarsNetFixture(SA, "cefoxitin", BLOOD, 2020, 64.0, "narrative"),
    # The PA+OSBF cell is one where the printed counts do not reconcile
    # (2,357/4,580 = 51.46). The narrative independently states 52, which
    # corroborates the printed %R rather than the printed numerator.
    NarsNetFixture(SA, "cefoxitin", PA_OSBF, 2020, 52.0,
                   "narrative (corroborates the printed %R; the printed counts "
                   "give 51.46 and carry pct_mismatch)"),
    # "Ciprofloxacin resistance is seen in 62% ... from blood culture specimens
    #  and in 72% ... from PA & OSBF."
    NarsNetFixture(SA, "ciprofloxacin", BLOOD, 2020, 62.0, "narrative"),
    NarsNetFixture(SA, "ciprofloxacin", PA_OSBF, 2020, 72.0,
                   "narrative (corroborates the printed %R; the printed counts "
                   "give 71.49 and carry pct_mismatch)"),
    # "Resistance to erythromycin is 68% in blood culture isolates and 50% in
    #  isolates from PA & OSBF."
    NarsNetFixture(SA, "erythromycin", BLOOD, 2020, 68.0, "narrative"),
    NarsNetFixture(SA, "erythromycin", PA_OSBF, 2020, 50.0, "narrative"),
    # "Gentamicin resistance is observed in 26% of isolates from blood culture
    #  specimens and in 22% isolates from PA & OSBF specimens."
    NarsNetFixture(SA, "gentamicin", BLOOD, 2020, 26.0, "narrative"),
    NarsNetFixture(SA, "gentamicin", PA_OSBF, 2020, 22.0, "narrative"),

    # --- 2020 E. coli, Table 8 (p33 [29]) -----------------------------------
    NarsNetFixture(EC, "ampicillin", URINE, 2020, 87.0, "table 8 cell, p33",
                   expected_tested_n=7188, expected_resistant_n=6279),
    NarsNetFixture(EC, "colistin", URINE, 2020, 6.3, "table 8 cell, p33",
                   expected_tested_n=493, expected_resistant_n=31),

    # --- 2021 S. aureus, Ch.V narrative (p22 [13], p23 [14]) ----------------
    # "59% resistance to methicillin is observed in S. aureus isolates from
    #  blood, and resistance to methicillin in isolates from aspirated pus and
    #  other sterile body fluids is found to be 49% and 48% respectively
    #  (Table 4)." The three percentages are the prose's; the counts on the
    #  first are the Table 4 cell, hand-read off p24, so the two provenances
    #  corroborate each other rather than both coming from one rendering.
    NarsNetFixture(SA, "cefoxitin", BLOOD, 2021, 59.0,
                   "narrative (%R); table 4 cell, p24 (counts)",
                   expected_tested_n=5805, expected_resistant_n=3441),
    NarsNetFixture(SA, "cefoxitin", PUS_ASPIRATE, 2021, 49.0, "narrative"),
    NarsNetFixture(SA, "cefoxitin", OSBF, 2021, 48.0, "narrative"),
    # "Erythromycin resistance is observed in 63% of S. aureus isolated from
    #  blood, 51% from pus aspirates and 54% from OSBF (Table 4)."
    NarsNetFixture(SA, "erythromycin", BLOOD, 2021, 63.0, "narrative"),
    NarsNetFixture(SA, "erythromycin", PUS_ASPIRATE, 2021, 51.0, "narrative"),
    NarsNetFixture(SA, "erythromycin", OSBF, 2021, 54.0, "narrative"),
    # "Similar to the last four years linezolid resistance to S. aureus is 1%."
    # Stated without a stratum; all three columns print 1. Counts from the cell.
    NarsNetFixture(SA, "linezolid", BLOOD, 2021, 1.0,
                   "narrative (%R, no stratum named); table 4 cell, p24 (counts)",
                   expected_tested_n=5761, expected_resistant_n=36),
    # Teicoplanin joins the S. aureus panel in this edition and the chapter does
    # not mention it, so this one is the table and nothing else.
    NarsNetFixture(SA, "teicoplanin", OSBF, 2021, 1.0, "table 4 cell, p24",
                   expected_tested_n=96, expected_resistant_n=1),

    # --- 2021 E. coli, Ch.V narrative (p28 [19]) ----------------------------
    # "For non-beta-lactam antibiotics, 73% resistance is observed to
    #  ciprofloxacin, 59% to Trimethoprim-Sulfamethoxazole (TMP/SMX) and 11% to
    #  nitrofurantoin in urinary isolates. (Table 6)"
    NarsNetFixture(EC, "ciprofloxacin", URINE, 2021, 73.0,
                   "narrative (%R); table 6 cell, p29 (counts)",
                   expected_tested_n=15064, expected_resistant_n=11037),
    NarsNetFixture(EC, "nitrofurantoin", URINE, 2021, 11.0,
                   "narrative (%R); table 6 cell, p29 (counts)",
                   expected_tested_n=16229, expected_resistant_n=1725),
    # One of the two Urine cells whose printed numerator repeats its
    # denominator. The prose corroborates the printed %R, which is the figure
    # this row carries; the denominator is the table's and is sound.
    NarsNetFixture(EC, "cotrimoxazole", URINE, 2021, 59.0,
                   "narrative (corroborates the printed %R; the printed "
                   "numerator repeats the denominator and is corrupt in "
                   "source); table 6 cell, p29 (denominator)",
                   expected_tested_n=8918),
    # The four Blood cells the chapter states. Every one of them sits in the
    # sub-column whose numerator is corrupt, so the prose is the only
    # independent confirmation of these percentages, and the denominators are
    # the table's.
    # "Similarly, in E. coli isolates from blood, percentage resistance to
    #  non-beta-lactam antibiotics observed is 63% to ciprofloxacin, 54% to
    #  TMP/SMX. 43% isolates from blood show resistance to piperacillin
    #  tazobactam."
    NarsNetFixture(EC, "ciprofloxacin", BLOOD, 2021, 63.0,
                   "narrative (corroborates the printed %R; the Blood "
                   "numerator sub-column is corrupt in source); table 6 cell, "
                   "p29 (denominator)",
                   expected_tested_n=1551),
    NarsNetFixture(EC, "cotrimoxazole", BLOOD, 2021, 54.0,
                   "narrative (corroborates the printed %R; the Blood "
                   "numerator sub-column is corrupt in source); table 6 cell, "
                   "p29 (denominator)",
                   expected_tested_n=1289),
    NarsNetFixture(EC, "piperacillin-tazobactam", BLOOD, 2021, 43.0,
                   "narrative (corroborates the printed %R; the Blood "
                   "numerator sub-column is corrupt in source); table 6 cell, "
                   "p29 (denominator)",
                   expected_tested_n=1350),
    # "Carbapenem resistance observed in E. coli isolates from blood is up to
    #  33%." Ertapenem is the highest of the three carbapenems in that column
    #  (ertapenem 33, imipenem 29, meropenem 25), so "up to 33%" names it.
    NarsNetFixture(EC, "ertapenem", BLOOD, 2021, 33.0,
                   "narrative (corroborates the printed %R; the Blood "
                   "numerator sub-column is corrupt in source); table 6 cell, "
                   "p29 (denominator)",
                   expected_tested_n=406),
    # Three drugs new to the E. coli panel in this edition, none of them named
    # in the chapter: table only, from the two columns that reconcile.
    NarsNetFixture(EC, "amikacin", PUS_ASPIRATE, 2021, 24.0, "table 6 cell, p29",
                   expected_tested_n=5399, expected_resistant_n=1280),
    NarsNetFixture(EC, "cefuroxime", URINE, 2021, 79.0, "table 6 cell, p29",
                   expected_tested_n=3257, expected_resistant_n=2581),
    NarsNetFixture(EC, "fosfomycin", URINE, 2021, 7.0, "table 6 cell, p29",
                   expected_tested_n=855, expected_resistant_n=58),
]


def index_records(records):
    return {
        (r.organism, r.antibiotic, r.specimen, r.source_report_year): r
        for r in records
    }


def check_narsnet_fixtures(records, fixtures=None):
    """Return (passes, failures). A failure means the parser is wrong."""
    fixtures = NARSNET_FIXTURES if fixtures is None else fixtures
    index = index_records(records)
    passes, failures = [], []
    for fx in fixtures:
        rec = index.get((fx.organism, fx.antibiotic, fx.specimen, fx.year))
        if rec is None:
            failures.append("{}: no record extracted".format(fx.label))
            continue
        if rec.resistant_pct is None:
            failures.append("{}: no percentage extracted".format(fx.label))
            continue
        if abs(rec.resistant_pct - fx.expected_pct) > fx.tolerance:
            failures.append(
                "{}: expected {}% ({}), got {}%".format(
                    fx.label, fx.expected_pct, fx.note, rec.resistant_pct
                )
            )
            continue
        if fx.expected_tested_n is not None and rec.tested_n != fx.expected_tested_n:
            failures.append(
                "{}: expected denominator {}, got {}".format(
                    fx.label, fx.expected_tested_n, rec.tested_n
                )
            )
            continue
        if (
            fx.expected_resistant_n is not None
            and rec.resistant_n != fx.expected_resistant_n
        ):
            failures.append(
                "{}: expected numerator {}, got {}".format(
                    fx.label, fx.expected_resistant_n, rec.resistant_n
                )
            )
            continue
        passes.append(fx.label)
    return passes, failures


def internal_consistency(records):
    """Rows whose printed percentage disagrees with their own printed counts.

    Only rows whose numerator is `printed` can reach this: a corrupt cell prints
    a figure that is not its numerator, so there is nothing for the percentage
    to disagree with, and folding those rows in here would change what the
    `pct_mismatch` count means.
    """
    return [r for r in records if any(f.startswith("pct_mismatch") for f in r.flags)]


def summarise_corrupt_numerators(records):
    """Every declared corrupt-numerator block, against the rows it covers.

    Descriptive only. The declaration has already done its work in the parser;
    what this adds is how many cells inside a declared block do nonetheless
    agree with the percentage printed beside them, and which. Reporting them
    rather than exempting them keeps the judgement -- that the unit of the
    defect is the sub-column, not the cell -- where a reader can see it.

    A block matching no rows is returned with a zero count rather than dropped,
    so a declaration left behind by a change of scope shows up instead of
    quietly doing nothing.
    """
    out = []
    for entry in CORRUPT_NUMERATORS:
        covered = [
            r
            for r in records
            if r.source_report_year == entry.year
            and r.organism == entry.organism
            and r.specimen == entry.specimen
            and r.numerator_status == NUMERATOR_CORRUPT
        ]
        agreeing = []
        for r in sorted(covered, key=lambda r: r.antibiotic):
            if not r.tested_n or r.resistant_n is None or r.reported_pct is None:
                continue
            computed = 100.0 * r.resistant_n / r.tested_n
            # `pct_tolerance` wants the percentage as printed and the record
            # keeps it as a float. "%g" recovers the printed form: no cell in
            # any of the six tables read so far prints a trailing ".0", so a
            # whole-number float was printed as a whole number.
            printed = "%g" % r.reported_pct
            if abs(r.reported_pct - computed) <= pct_tolerance(printed):
                agreeing.append(
                    {
                        "antibiotic": r.antibiotic,
                        "tested_n": r.tested_n,
                        "resistant_n": r.resistant_n,
                        "reported_pct": r.reported_pct,
                        "computed_pct": round(computed, 2),
                    }
                )
        out.append(
            {
                "source_report_year": entry.year,
                "organism": entry.organism,
                "specimen": entry.specimen,
                "scope": (
                    "whole sub-column"
                    if entry.antibiotics is None
                    else sorted(entry.antibiotics)
                ),
                "cells": len(covered),
                "cells_agreeing_with_their_printed_pct": len(agreeing),
                "agreeing": agreeing,
                "note": entry.note,
            }
        )
    return out


# --- cross-column checks ----------------------------------------------------

DEGENERATE_FLAG = "composite_disagrees_with_its_only_stratum"


def _constituents(specimen: str) -> frozenset:
    return frozenset(specimen.split("+"))


def find_degenerate_composite_disagreements(records):
    """The cross-column check: a composite covering exactly one reported stratum.

    When a drug is reported for one specimen only -- the other blocks greyed out
    -- a composite column and that single stratum column describe the same
    isolates. Two renderings of one set of isolates must print the same counts.

    Returns one finding per disagreement, each naming both columns and both
    counts. An empty list means every degenerate composite in the data agrees
    with its stratum, which is the expected result everywhere except 2019
    E. coli nitrofurantoin.
    """
    grouped: dict = {}
    for r in records:
        grouped.setdefault(
            (r.organism, r.source_report_year, r.antibiotic), []
        ).append(r)

    findings = []
    for (organism, year, antibiotic), rows in sorted(grouped.items(), key=str):
        composites = [r for r in rows if is_composite(r.specimen)]
        for comp in composites:
            others = [r for r in rows if r.specimen != comp.specimen]
            covered = [
                r for r in others
                if _constituents(r.specimen) <= _constituents(comp.specimen)
            ]
            # Degenerate only when a single other column accounts for the whole
            # composite. Anything else is a partition, handled descriptively.
            if len(covered) != 1:
                continue
            stratum = covered[0]
            if _constituents(stratum.specimen) == _constituents(comp.specimen):
                continue
            if comp.tested_n != stratum.tested_n:
                continue
            if comp.resistant_n == stratum.resistant_n:
                continue
            findings.append(
                {
                    "organism": organism,
                    "source_report_year": year,
                    "antibiotic": antibiotic,
                    "composite_specimen": comp.specimen,
                    "only_reported_stratum": stratum.specimen,
                    "shared_tested_n": comp.tested_n,
                    "composite_resistant_n": comp.resistant_n,
                    "stratum_resistant_n": stratum.resistant_n,
                    "difference": (
                        None
                        if comp.resistant_n is None or stratum.resistant_n is None
                        else comp.resistant_n - stratum.resistant_n
                    ),
                    "composite_pct": comp.resistant_pct,
                    "stratum_pct": stratum.resistant_pct,
                    "note": (
                        "The drug is reported for {} only in this edition; the "
                        "other specimen blocks are greyed out. Both columns "
                        "therefore describe the same isolates and print the same "
                        "denominator, but their numerators differ.".format(
                            stratum.specimen
                        )
                    ),
                }
            )
    return findings


def apply_degenerate_composite_flags(records):
    """Flag both sides of every degenerate disagreement. Returns the findings."""
    findings = find_degenerate_composite_disagreements(records)
    index = index_records(records)
    for f in findings:
        for specimen in (f["composite_specimen"], f["only_reported_stratum"]):
            rec = index.get(
                (f["organism"], f["antibiotic"], specimen, f["source_report_year"])
            )
            if rec is None:
                continue
            flag = "{}(composite={},stratum={})".format(
                DEGENERATE_FLAG, f["composite_resistant_n"], f["stratum_resistant_n"]
            )
            if flag not in rec.flags:
                rec.flags.append(flag)
    return findings


def summarise_composite_sums(records):
    """Composite columns against the sum of a full partition. Descriptive only.

    No flag is raised from this. Across 2019 and 2020 the difference is the rule
    rather than the exception, so a flag would mark nearly every composite row
    and say nothing. See the module docstring.
    """
    grouped: dict = {}
    for r in records:
        grouped.setdefault(
            (r.organism, r.source_report_year, r.antibiotic), []
        ).append(r)

    out = []
    for (organism, year, antibiotic), rows in sorted(grouped.items(), key=str):
        for comp in [r for r in rows if is_composite(r.specimen)]:
            others = [r for r in rows if r.specimen != comp.specimen]
            parts = [
                r for r in others
                if _constituents(r.specimen) < _constituents(comp.specimen)
            ]
            if len(parts) < 2:
                continue
            union: set = set()
            disjoint = True
            for p in parts:
                cons = _constituents(p.specimen)
                if union & cons:
                    disjoint = False
                    break
                union |= cons
            if not disjoint or union != _constituents(comp.specimen):
                continue
            tested_sum = sum(p.tested_n for p in parts if p.tested_n is not None)
            resistant_sum = sum(
                p.resistant_n for p in parts if p.resistant_n is not None
            )
            out.append(
                {
                    "organism": organism,
                    "source_report_year": year,
                    "antibiotic": antibiotic,
                    "composite_specimen": comp.specimen,
                    "partition": sorted(p.specimen for p in parts),
                    "composite_tested_n": comp.tested_n,
                    "partition_tested_sum": tested_sum,
                    "tested_difference": (
                        None if comp.tested_n is None else comp.tested_n - tested_sum
                    ),
                    "composite_resistant_n": comp.resistant_n,
                    "partition_resistant_sum": resistant_sum,
                    "resistant_difference": (
                        None
                        if comp.resistant_n is None
                        else comp.resistant_n - resistant_sum
                    ),
                }
            )
    return out


# --- panel and specimen-column changes --------------------------------------

PANEL_CHANGED_FLAG = "narsnet_panel_changed"
SPECIMEN_COLUMNS_CHANGED_FLAG = "narsnet_specimen_columns_changed"


def narsnet_panel_by_edition(records):
    """Per organism and edition: the drug panel and the specimen columns."""
    panel: dict = {}
    for r in records:
        entry = panel.setdefault(
            r.organism, {}
        ).setdefault(r.source_report_year, {"antibiotics": set(), "specimens": set()})
        entry["antibiotics"].add(r.antibiotic)
        entry["specimens"].add(r.specimen)
    return {
        organism: {
            year: {
                "antibiotics": sorted(v["antibiotics"]),
                "specimens": sorted(v["specimens"]),
            }
            for year, v in sorted(years.items())
        }
        for organism, years in sorted(panel.items())
    }


def detect_narsnet_panel_changes(panel):
    """Differences between consecutive editions, per organism.

    Both axes matter and they change independently. Between 2019 and 2020 the
    E. coli drug panel is identical while the pooled specimen column disappears,
    so an edition-over-edition comparison of a pooled figure would be comparing
    a printed column against one that no longer exists.
    """
    changes = []
    for organism, years in panel.items():
        ordered = sorted(years)
        for prev, cur in zip(ordered, ordered[1:]):
            before, after = years[prev], years[cur]
            drugs_added = sorted(set(after["antibiotics"]) - set(before["antibiotics"]))
            drugs_removed = sorted(
                set(before["antibiotics"]) - set(after["antibiotics"])
            )
            spec_added = sorted(set(after["specimens"]) - set(before["specimens"]))
            spec_removed = sorted(set(before["specimens"]) - set(after["specimens"]))
            if not (drugs_added or drugs_removed or spec_added or spec_removed):
                continue
            changes.append(
                {
                    "organism": organism,
                    "from_edition": prev,
                    "to_edition": cur,
                    "antibiotics_added": drugs_added,
                    "antibiotics_removed": drugs_removed,
                    "specimen_columns_added": spec_added,
                    "specimen_columns_removed": spec_removed,
                }
            )
    return changes


def apply_narsnet_panel_flags(records):
    """Flag rows in an edition whose panel or specimen columns changed."""
    panel = narsnet_panel_by_edition(records)
    changes = detect_narsnet_panel_changes(panel)
    for change in changes:
        for r in records:
            if r.organism != change["organism"]:
                continue
            if r.source_report_year != change["to_edition"]:
                continue
            if change["antibiotics_added"] or change["antibiotics_removed"]:
                flag = "{}(from={})".format(PANEL_CHANGED_FLAG, change["from_edition"])
                if flag not in r.flags:
                    r.flags.append(flag)
            if change["specimen_columns_added"] or change["specimen_columns_removed"]:
                flag = "{}(from={})".format(
                    SPECIMEN_COLUMNS_CHANGED_FLAG, change["from_edition"]
                )
                if flag not in r.flags:
                    r.flags.append(flag)
    return changes


# --- cross-edition revisions ------------------------------------------------

REVISIONS_NOTE = (
    "Each NARS-Net edition reports its own reporting period only, with no "
    "retrospective multi-year table -- checked across all eight editions during "
    "the V3 investigation. No (organism, antibiotic, specimen, year) key is "
    "therefore covered by more than one edition, so cross-edition revision "
    "detection has nothing to compare. An empty result here is BY DESIGN and is "
    "not evidence that no revision occurred; it means the published reports "
    "provide no way to look. This mirrors rc_revisions.json, which is empty for "
    "the same structural reason on the AMRSN side."
)


def find_narsnet_cross_report_revisions(records):
    """Same key reported differently by two editions. Structurally always empty.

    Kept as a real check rather than a hardcoded empty list: if a future edition
    ever does print a retrospective table, this starts returning rows instead of
    silently continuing to claim there is nothing to find.
    """
    grouped: dict = {}
    for r in records:
        key = (r.organism, r.antibiotic, r.specimen, r.year)
        grouped.setdefault(key, []).append(r)

    revisions = []
    for key, rows in sorted(grouped.items(), key=str):
        editions = {r.source_report_year for r in rows}
        if len(editions) < 2:
            continue
        pcts = {r.source_report_year: r.resistant_pct for r in rows}
        if len(set(pcts.values())) < 2:
            continue
        organism, antibiotic, specimen, year = key
        revisions.append(
            {
                "organism": organism,
                "antibiotic": antibiotic,
                "specimen": specimen,
                "year": year,
                "by_edition": {str(k): v for k, v in sorted(pcts.items())},
            }
        )
    return revisions
