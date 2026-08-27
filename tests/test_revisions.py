"""Cross-report revision detection (spec section 2.1).

The headline claim of this project is that it can tell a genuine revision in
ICMR's data apart from a change in how ICMR printed the same number. These
tests pin that distinction down.
"""

from __future__ import annotations

from src.parsers.base import Record
from src.validate import find_cross_report_revisions


def rec(report_year, n, tested, pct, year=2022, antibiotic="piperacillin-tazobactam"):
    return Record(
        organism="Escherichia coli",
        antibiotic=antibiotic,
        year=year,
        susceptible_n=n,
        tested_n=tested,
        susceptible_pct=pct,
        source_report_year=report_year,
        source_table="Table X",
        source_url="https://example.invalid/",
        extracted_date="test",
        reported_pct=pct,
        computed_pct=round(100.0 * n / tested, 2) if tested else None,
    )


def test_detects_denominator_only_revision():
    """The real one: 5170/14729 becomes 5170/14728, percentage unchanged.

    A detector that only compared percentages would report nothing here.
    """
    revisions = find_cross_report_revisions(
        [rec(2022, 5170, 14729, 35.1), rec(2024, 5170, 14728, 35.1)]
    )
    assert len(revisions) == 1
    assert revisions[0]["kind"] == "count_revision"
    assert revisions[0]["tested_n_by_report"] == {2022: 14729, 2024: 14728}
    assert revisions[0]["tested_n_spread"] == 1


def test_ignores_rounding_only_difference():
    """14.94% and 14.9% from identical counts is precision, not revision."""
    revisions = find_cross_report_revisions(
        [rec(2023, 1021, 6833, 14.94), rec(2024, 1021, 6833, 14.9)]
    )
    assert revisions == []


def test_detects_percentage_revision_with_stable_counts():
    revisions = find_cross_report_revisions(
        [rec(2023, 1021, 6833, 14.9), rec(2024, 1021, 6833, 21.4)]
    )
    assert len(revisions) == 1
    assert revisions[0]["kind"] == "percentage_revision"


def test_single_edition_is_not_a_revision():
    assert find_cross_report_revisions([rec(2024, 5170, 14728, 35.1)]) == []


def test_identical_across_editions_is_not_a_revision():
    revisions = find_cross_report_revisions(
        [
            rec(2022, 5170, 14729, 35.1),
            rec(2023, 5170, 14729, 35.1),
            rec(2024, 5170, 14729, 35.1),
        ]
    )
    assert revisions == []


def test_count_revisions_sort_before_percentage_revisions():
    revisions = find_cross_report_revisions(
        [
            rec(2023, 100, 1000, 10.0, antibiotic="meropenem"),
            rec(2024, 100, 1000, 25.0, antibiotic="meropenem"),
            rec(2023, 5170, 14729, 35.1),
            rec(2024, 5170, 14728, 35.1),
        ]
    )
    assert [r["kind"] for r in revisions] == [
        "count_revision",
        "percentage_revision",
    ]
