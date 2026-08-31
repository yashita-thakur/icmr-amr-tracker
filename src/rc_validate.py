"""Validation for the V2 Regional Centre dataset.

Three checks, mirroring `validate.py` for V1:

* **Fixtures** -- individual RC cells read by hand from the printed tables and
  asserted against extraction.
* **Internal consistency** -- every RC cell's printed percentage recomputed from
  its own numerator and denominator (this is applied in `rc_parser` too; here it
  is surfaced for reporting).
* **RC panel change detection** -- for each organism, the set of Regional
  Centres present in each edition, compared against the earliest edition that
  covers it. A difference (RC added or dropped) is reported and flagged rather
  than averaged over, because the RC codes are de-identified in the reports and
  the tables carry no code-to-institution key, so an RC that appears in two
  editions cannot be assumed to be the same institution once the panel around
  it has moved.

Cross-edition *revision* detection is deliberately kept (`find_rc_cross_report_
revisions`) but is expected to return nothing: the RC-wise tables are
single-year cross-sections, so no (organism, RC, antibiotic, year) key is
covered by more than one edition. See the README section "Regional Centre
tables are a single-year cross-section".
"""

from __future__ import annotations

from dataclasses import dataclass

from .validate import ROUNDING_TOLERANCE


@dataclass(frozen=True)
class RCFixture:
    organism: str
    regional_centre: str
    antibiotic: str
    source_report_year: int
    expected_pct: float
    note: str
    expected_susceptible_n: int | None = None
    expected_tested_n: int | None = None
    tolerance: float = 0.1

    @property
    def label(self) -> str:
        return "{} / {} / {} (from {} edition)".format(
            self.organism, self.regional_centre, self.antibiotic,
            self.source_report_year,
        )


# Every fixture is a cell read straight off the printed RC-wise table. Column
# order per organism is the panel as printed:
#   Enterobacterales: piperacillin-tazobactam, cefotaxime, ceftazidime,
#     ertapenem, imipenem, meropenem, amikacin, ciprofloxacin, levofloxacin
#   S. aureus: cefoxitin, oxacillin, vancomycin, teicoplanin, erythromycin,
#     tetracycline, tigecycline, ciprofloxacin, clindamycin, cotrimoxazole,
#     linezolid
RC_FIXTURES: list[RCFixture] = [
    # --- E. coli, 2023 edition, Table 3.10 ---
    RCFixture(
        "Escherichia coli", "RC1", "meropenem", 2023, 51.4,
        "2023 Table 3.10, RC1 row: 201/391", 201, 391,
    ),
    RCFixture(
        "Escherichia coli", "RC3", "imipenem", 2023, 84.3,
        "2023 Table 3.10, RC3 row: 425/504", 425, 504,
    ),
    RCFixture(
        "Escherichia coli", "RC5", "amikacin", 2023, 88.6,
        "2023 Table 3.10, RC5 row: 271/306", 271, 306,
    ),
    # --- E. coli, 2024 edition, Table 2.10 ---
    RCFixture(
        "Escherichia coli", "RC2", "meropenem", 2024, 54.7,
        "2024 Table 2.10, RC2 row: 2212/4041", 2212, 4041,
    ),
    RCFixture(
        "Escherichia coli", "RC3", "ertapenem", 2024, 83.1,
        "2024 Table 2.10, RC3 row: 409/492", 409, 492,
    ),
    # --- S. aureus, 2022 edition, Table 6.3 ---
    RCFixture(
        "Staphylococcus aureus", "RC4", "vancomycin", 2022, 100.0,
        "2022 Table 6.3, RC4 row: 1862/1862", 1862, 1862,
    ),
    RCFixture(
        "Staphylococcus aureus", "RC4", "cefoxitin", 2022, 76.2,
        "2022 Table 6.3, RC4 row: 1421/1866", 1421, 1866,
    ),
    RCFixture(
        "Staphylococcus aureus", "RC8", "clindamycin", 2022, 97.5,
        "2022 Table 6.3, RC8 row: 231/237", 231, 237,
    ),
    # --- S. aureus, 2024 edition, Table 6.3 ---
    RCFixture(
        "Staphylococcus aureus", "RC8", "clindamycin", 2024, 97.5,
        "2024 Table 6.3, RC8 row: 308/316", 308, 316,
    ),
    RCFixture(
        "Staphylococcus aureus", "RC14", "cefoxitin", 2024, 54.0,
        "2024 Table 6.3, RC14 row: 429/795", 429, 795,
    ),
]


def index_rc_records(records) -> dict:
    idx = {}
    for r in records:
        idx[
            (r.organism, r.regional_centre, r.antibiotic, r.source_report_year)
        ] = r
    return idx


def check_rc_fixtures(records, fixtures=None):
    """Return (passes, failures) as lists of human-readable strings."""
    fixtures = RC_FIXTURES if fixtures is None else fixtures
    idx = index_rc_records(records)
    passes, failures = [], []

    for fx in fixtures:
        key = (fx.organism, fx.regional_centre, fx.antibiotic, fx.source_report_year)
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


def rc_internal_consistency(records):
    """RC records whose printed percentage does not fully reconcile with numerator/denominator."""
    return [r for r in records if any(f.startswith("pct_mismatch") for f in r.flags)]


# --- RC panel change detection ------------------------------------------------

PANEL_CHANGED_FLAG = "rc_panel_changed"


def rc_panel_by_edition(records) -> dict:
    """{organism: {report_year: sorted list of RC labels present}}."""
    panel: dict = {}
    for r in records:
        panel.setdefault(r.organism, {}).setdefault(r.source_report_year, set()).add(
            r.regional_centre
        )
    return {
        org: {
            yr: sorted(years[yr], key=_rc_sort_key) for yr in sorted(years)
        }
        for org, years in panel.items()
    }


def _rc_sort_key(label: str):
    digits = "".join(ch for ch in label if ch.isdigit())
    return int(digits) if digits else 0


def detect_rc_panel_changes(records) -> list:
    """Per organism, compare each edition's RC set against the earliest one.

    Returns a list of dicts, one per (organism, edition) whose RC set differs
    from that organism's baseline edition. The baseline edition itself is not
    listed. Editions whose set is identical to the baseline are not listed.
    """
    panel = rc_panel_by_edition(records)
    changes = []
    for organism, by_year in sorted(panel.items()):
        years = sorted(by_year)
        if len(years) < 2:
            continue
        baseline_year = years[0]
        baseline = set(by_year[baseline_year])
        for yr in years[1:]:
            now = set(by_year[yr])
            added = sorted(now - baseline, key=_rc_sort_key)
            dropped = sorted(baseline - now, key=_rc_sort_key)
            if not added and not dropped:
                continue
            changes.append(
                {
                    "organism": organism,
                    "baseline_edition": baseline_year,
                    "edition": yr,
                    "baseline_rc_count": len(baseline),
                    "edition_rc_count": len(now),
                    "added": added,
                    "dropped": dropped,
                }
            )
    return changes


def apply_rc_panel_flags(records):
    """Append the `rc_panel_changed(...)` flag in place to every record from an
    (organism, edition) whose RC panel differs from that organism's baseline.

    The flag string carries the diff, e.g.
    ``rc_panel_changed(baseline=2023,added=[],dropped=[RC15])``.
    """
    changes = detect_rc_panel_changes(records)
    per_edition = {
        (c["organism"], c["edition"]): c for c in changes
    }
    for r in records:
        c = per_edition.get((r.organism, r.source_report_year))
        if c is None:
            continue
        flag = "{}(baseline={},added=[{}],dropped=[{}])".format(
            PANEL_CHANGED_FLAG,
            c["baseline_edition"],
            " ".join(c["added"]),
            " ".join(c["dropped"]),
        )
        if flag not in r.flags:
            r.flags.append(flag)
    return changes


# --- cross-edition revisions (structurally near-empty; see module docstring) --


def find_rc_cross_report_revisions(records):
    """Same detector as V1, keyed on (organism, RC, antibiotic, year).

    Kept for parity and as an explicit guard: if this ever returns a non-empty
    list, an edition has started republishing a prior year's RC-wise table and
    the single-year-cross-section assumption in the README needs revisiting.
    """
    buckets: dict = {}
    for r in records:
        buckets.setdefault(
            (r.organism, r.regional_centre, r.antibiotic, r.year), []
        ).append(r)

    revisions = []
    for (organism, rc, antibiotic, year), group in sorted(buckets.items()):
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
            continue
        revisions.append(
            {
                "kind": kind,
                "organism": organism,
                "regional_centre": rc,
                "antibiotic": antibiotic,
                "year": year,
                "susceptible_pct_by_report": dict(sorted(pcts.items())),
            }
        )
    return revisions
