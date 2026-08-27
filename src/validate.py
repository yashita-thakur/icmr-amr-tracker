"""Fixture validation (spec section 4.5).

Every fixture below is a value printed in an ICMR report that we can check our
extraction against. If the pipeline disagrees with any of these, the parser is
wrong and its output must not be used.

Provenance of each fixture is recorded in `note`. Two kinds appear:

* "table"     -- read out of the trend table itself.
* "narrative" -- stated in the chapter's prose, which the report writes
                 independently of the table. These are the more valuable
                 checks: prose and table are separate renderings of the same
                 underlying number, so agreement is real corroboration rather
                 than a tautology.

Note on spec section 4: the spec listed E. coli / meropenem / 2024 as
"62.9% (7594/12061...)" with the numerator marked uncertain. The 2024 edition,
Table 2.6, prints **7587/12061**, which is 62.90%. (7594/12061 would round to
63.0%.) The fixture below uses the verified value.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Fixture:
    organism: str
    antibiotic: str
    year: int
    source_report_year: int
    expected_pct: float
    note: str
    expected_susceptible_n: int | None = None
    expected_tested_n: int | None = None
    tolerance: float = 0.1

    @property
    def label(self) -> str:
        return "{} / {} / {} (from {} report)".format(
            self.organism, self.antibiotic, self.year, self.source_report_year
        )


# --- fixtures verified against the 2024 edition (8th) -----------------------

FIXTURES: list[Fixture] = [
    # Spec section 4 anchor, with the numerator corrected against Table 2.6.
    Fixture(
        "Escherichia coli", "meropenem", 2024, 2024, 62.9,
        "2024 edition Table 2.6, corroborated by Ch.2 narrative "
        "('meropenem susceptibility decreased from 73.2% to 62.9%')",
        expected_susceptible_n=7587, expected_tested_n=12061,
    ),
    # Spec section 4 anchor.
    Fixture(
        "Klebsiella pneumoniae", "meropenem", 2024, 2024, 35.1,
        "2024 edition Table 2.7, corroborated by Ch.2 narrative "
        "('meropenem dropped from 48.1% to 35.1%')",
    ),

    # E. coli, 2024 edition narrative (Chapter 2).
    Fixture("Escherichia coli", "meropenem", 2017, 2024, 73.2, "narrative"),
    Fixture("Escherichia coli", "imipenem", 2017, 2024, 81.4, "narrative"),
    Fixture("Escherichia coli", "imipenem", 2024, 2024, 57.6, "narrative"),
    Fixture("Escherichia coli", "ertapenem", 2017, 2024, 67.4, "narrative"),
    Fixture("Escherichia coli", "ertapenem", 2024, 2024, 61.6, "narrative"),
    Fixture("Escherichia coli", "ceftazidime", 2017, 2024, 23.5, "narrative"),
    Fixture("Escherichia coli", "ceftazidime", 2024, 2024, 27.5, "narrative"),
    Fixture("Escherichia coli", "ciprofloxacin", 2017, 2024, 19.2, "narrative"),
    Fixture("Escherichia coli", "ciprofloxacin", 2024, 2024, 10.6, "narrative"),
    Fixture(
        "Escherichia coli", "piperacillin-tazobactam", 2017, 2024, 56.8, "table"
    ),

    # K. pneumoniae, 2024 edition narrative (Chapter 2).
    Fixture(
        "Klebsiella pneumoniae", "piperacillin-tazobactam", 2017, 2024, 42.6,
        "narrative",
    ),
    Fixture(
        "Klebsiella pneumoniae", "piperacillin-tazobactam", 2024, 2024, 26.0,
        "narrative",
    ),
    Fixture("Klebsiella pneumoniae", "cefotaxime", 2017, 2024, 21.8, "narrative"),
    Fixture("Klebsiella pneumoniae", "cefotaxime", 2024, 2024, 20.3, "narrative"),
    Fixture("Klebsiella pneumoniae", "ceftazidime", 2017, 2024, 27.6, "narrative"),
    Fixture("Klebsiella pneumoniae", "ceftazidime", 2024, 2024, 23.7, "narrative"),
    Fixture("Klebsiella pneumoniae", "imipenem", 2017, 2024, 58.5, "narrative"),
    Fixture("Klebsiella pneumoniae", "imipenem", 2024, 2024, 31.2, "narrative"),
    Fixture("Klebsiella pneumoniae", "meropenem", 2017, 2024, 48.1, "narrative"),
    Fixture("Klebsiella pneumoniae", "ertapenem", 2017, 2024, 45.4, "narrative"),
    Fixture("Klebsiella pneumoniae", "ertapenem", 2024, 2024, 36.8, "narrative"),
    Fixture("Klebsiella pneumoniae", "amikacin", 2017, 2024, 48.9, "narrative"),
    Fixture("Klebsiella pneumoniae", "amikacin", 2024, 2024, 39.9, "narrative"),
    Fixture("Klebsiella pneumoniae", "ciprofloxacin", 2024, 2024, 20.4, "narrative"),
    Fixture("Klebsiella pneumoniae", "levofloxacin", 2017, 2024, 28.3, "narrative"),
    Fixture("Klebsiella pneumoniae", "levofloxacin", 2024, 2024, 24.8, "narrative"),
]

# --- V1.1: non-fermenters and staphylococci ---------------------------------
#
# The NFGNB and Staph chapters carry far less prose than Chapter 2, so several
# of these are derived from resistance figures stated in the executive summary.
# For P. aeruginosa the reports' susceptible and resistant percentages sum to
# 100 exactly (no intermediate category is published for it), which makes those
# conversions exact rather than approximate.

FIXTURES += [
    # A. baumannii. The spec's own anchor: "meropenem ... resistance 91.0%".
    Fixture(
        "Acinetobacter baumannii", "meropenem", 2024, 2024, 9.0,
        "2024 exec summary: 'Resistance to meropenem in A. baumannii was "
        "recorded as 91.0% in the year 2024' -> 9.0% susceptible",
    ),
    Fixture(
        "Acinetobacter baumannii", "minocycline", 2024, 2024, 70.2,
        "2024 narrative: 'Susceptibility of A. baumannii to minocycline was "
        "close to 70%'", tolerance=0.6,
    ),

    # P. aeruginosa, from the NFGNB 'Highlights of AMR trends' block.
    Fixture(
        "Pseudomonas aeruginosa", "ciprofloxacin", 2017, 2024, 57.8,
        "narrative: 'ciprofloxacin showed a susceptibility rate of 57.8% in 2017'",
    ),
    Fixture(
        "Pseudomonas aeruginosa", "ciprofloxacin", 2022, 2024, 47.4,
        "narrative: '...which declined to 47.4% in 2022'",
    ),
    Fixture(
        "Pseudomonas aeruginosa", "ciprofloxacin", 2024, 2024, 57.0,
        "narrative: '...then increased to 57% in 2024'",
    ),
    Fixture(
        "Pseudomonas aeruginosa", "meropenem", 2017, 2024, 68.7,
        "narrative: carbapenem-resistant P. aeruginosa 'from 31.3% in 2017' "
        "(meropenem) -> 68.7% susceptible",
    ),
    Fixture(
        "Pseudomonas aeruginosa", "meropenem", 2024, 2024, 62.0,
        "narrative: '...to 38% in 2024' (meropenem) -> 62.0% susceptible",
    ),
    Fixture(
        "Pseudomonas aeruginosa", "imipenem", 2024, 2024, 56.9,
        "narrative: imipenem resistance '43% in 2024' -> ~57% susceptible",
        tolerance=0.6,
    ),

    # Staphylococci. Anti-MRSA agents are stated to be near-100% effective.
    Fixture(
        "MRSA", "vancomycin", 2024, 2024, 100.0,
        "2024 narrative: anti-MRSA agents 'showing 100% effectiveness against "
        "MRSA isolates'",
    ),
    Fixture(
        "MRSA", "teicoplanin", 2024, 2024, 100.0,
        "2024 narrative: teicoplanin 100% effective against MRSA",
    ),
    # Definitional, and the strongest available check that the MRSA table has
    # been read correctly: MRSA is by definition methicillin/cefoxitin
    # resistant, so cefoxitin susceptibility must be 0%.
    Fixture(
        "MRSA", "cefoxitin", 2024, 2024, 0.0,
        "definitional: MRSA is cefoxitin-resistant, so 0% susceptible",
    ),
    Fixture(
        "MRSA", "cefoxitin", 2017, 2024, 0.0,
        "definitional: MRSA is cefoxitin-resistant, so 0% susceptible",
    ),
    Fixture(
        "Staphylococcus aureus", "vancomycin", 2024, 2024, 100.0,
        "2024 narrative: vancomycin retains full activity against S. aureus",
    ),
]

# Still out of scope: the frequently quoted "MRSA rose from 33% in 2017 to
# nearly 53% in 2024" is MRSA PREVALENCE -- the share of S. aureus that is
# methicillin-resistant -- and comes from the isolate-distribution chapter, not
# from any susceptibility trend table. It is deliberately NOT asserted against
# Table 6.9, which reports how susceptible MRSA isolates are to each drug.
# Conflating the two would be a category error.


def index_records(records) -> dict:
    """Key records by (organism, antibiotic, year, source_report_year)."""
    idx = {}
    for r in records:
        idx[(r.organism, r.antibiotic, r.year, r.source_report_year)] = r
    return idx


def check_fixtures(records, fixtures=None):
    """Return (passes, failures) as lists of human-readable strings."""
    fixtures = FIXTURES if fixtures is None else fixtures
    idx = index_records(records)
    passes, failures = [], []

    for fx in fixtures:
        key = (fx.organism, fx.antibiotic, fx.year, fx.source_report_year)
        rec = idx.get(key)
        if rec is None:
            failures.append("MISSING  {} -- no record extracted".format(fx.label))
            continue

        if rec.susceptible_pct is None:
            failures.append("NO PCT   {} -- record has no percentage".format(fx.label))
            continue

        delta = abs(rec.susceptible_pct - fx.expected_pct)
        if delta > fx.tolerance:
            failures.append(
                "PCT      {} -- expected {}%, got {}% (delta {:.2f})".format(
                    fx.label, fx.expected_pct, rec.susceptible_pct, delta
                )
            )
            continue

        if (
            fx.expected_susceptible_n is not None
            and rec.susceptible_n != fx.expected_susceptible_n
        ):
            failures.append(
                "NUMER    {} -- expected n={}, got n={}".format(
                    fx.label, fx.expected_susceptible_n, rec.susceptible_n
                )
            )
            continue

        if fx.expected_tested_n is not None and rec.tested_n != fx.expected_tested_n:
            failures.append(
                "DENOM    {} -- expected N={}, got N={}".format(
                    fx.label, fx.expected_tested_n, rec.tested_n
                )
            )
            continue

        passes.append("ok  {} = {}%".format(fx.label, rec.susceptible_pct))

    return passes, failures


def internal_consistency(records):
    """Flag records where the printed percentage disagrees with numerator/denominator."""
    return [r for r in records if any(f.startswith("pct_mismatch") for f in r.flags)]


# A percentage difference at or below this, with identical underlying counts,
# is a printing-precision artefact rather than a revision.
ROUNDING_TOLERANCE = 0.15


def find_cross_report_revisions(records):
    """Detect the same (organism, antibiotic, year) reported differently by
    different report editions -- spec section 2.1.

    This is a genuine data-integrity finding about ICMR's own publications, not
    a bug in this pipeline.

    Two kinds of difference must not be conflated:

    * `count_revision`  -- the numerator or denominator itself changed between
      editions. E. coli / piperacillin-tazobactam / 2022 is reported as
      5170/14729 by the 2022 and 2023 editions but 5170/14728 by the 2024
      edition: one isolate was removed on de-duplication. This is a real
      revision of the underlying data.

    * `percentage_revision` -- counts agree but the printed percentage moved by
      more than rounding can explain.

    Differences that are ONLY printing precision (the 2023 edition prints
    14.94% where the 2024 edition prints 14.9% for the identical 1021/6833) are
    not revisions and are excluded. Reporting them as such would overstate the
    instability of ICMR's data.
    """
    buckets: dict = {}
    for r in records:
        buckets.setdefault((r.organism, r.antibiotic, r.year), []).append(r)

    revisions = []
    for (organism, antibiotic, year), group in sorted(buckets.items()):
        by_report = {r.source_report_year: r for r in group}
        if len(by_report) < 2:
            continue

        counts = {
            srp: (r.susceptible_n, r.tested_n)
            for srp, r in by_report.items()
            if r.susceptible_n is not None and r.tested_n is not None
        }
        pcts = {
            srp: r.susceptible_pct
            for srp, r in by_report.items()
            if r.susceptible_pct is not None
        }

        counts_changed = len(set(counts.values())) > 1
        pct_spread = (max(pcts.values()) - min(pcts.values())) if len(pcts) > 1 else 0.0

        if counts_changed:
            kind = "count_revision"
        elif pct_spread > ROUNDING_TOLERANCE:
            kind = "percentage_revision"
        else:
            continue  # rounding / printing precision only

        denominators = {srp: n for srp, (_s, n) in sorted(counts.items())}
        numerators = {srp: s for srp, (s, _n) in sorted(counts.items())}
        entry = {
            "kind": kind,
            "organism": organism,
            "antibiotic": antibiotic,
            "year": year,
            "susceptible_pct_by_report": dict(sorted(pcts.items())),
            "susceptible_n_by_report": numerators,
            "tested_n_by_report": denominators,
            "pct_spread_pp": round(pct_spread, 2),
        }
        if denominators:
            entry["tested_n_spread"] = max(denominators.values()) - min(
                denominators.values()
            )
        revisions.append(entry)

    revisions.sort(
        key=lambda d: (d["kind"] != "count_revision", -d["pct_spread_pp"])
    )
    return revisions
