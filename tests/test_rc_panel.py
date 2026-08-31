"""RC panel-change detection and the (near-empty by design) RC revision check.

These are pure unit tests over synthetic records -- no PDFs required. The
headline V2 claim is that a change in *which* Regional Centres an edition
reports is detected and flagged, never averaged over, because the RC codes are
anonymised and carry no institution key.
"""

from __future__ import annotations

from src.parsers.rc_parser import RCRecord
from src.rc_validate import (
    apply_rc_panel_flags,
    detect_rc_panel_changes,
    find_rc_cross_report_revisions,
    rc_panel_by_edition,
)


def rc(organism, centre, antibiotic, report_year, n=50, tested=100, pct=50.0):
    return RCRecord(
        organism=organism,
        regional_centre=centre,
        antibiotic=antibiotic,
        year=report_year,
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


def _panel(organism, report_year, centres):
    return [rc(organism, c, "meropenem", report_year) for c in centres]


def test_identical_panel_across_editions_is_not_flagged():
    records = _panel("E. coli", 2023, ["RC1", "RC2", "RC3"]) + _panel(
        "E. coli", 2024, ["RC1", "RC2", "RC3"]
    )
    assert detect_rc_panel_changes(records) == []
    apply_rc_panel_flags(records)
    assert all(r.flags == [] for r in records)


def test_dropped_centre_is_detected_against_the_earliest_edition():
    records = _panel("E. coli", 2023, ["RC1", "RC2", "RC3"]) + _panel(
        "E. coli", 2024, ["RC1", "RC3"]
    )
    changes = detect_rc_panel_changes(records)
    assert len(changes) == 1
    c = changes[0]
    assert c["organism"] == "E. coli"
    assert c["baseline_edition"] == 2023
    assert c["edition"] == 2024
    assert c["dropped"] == ["RC2"]
    assert c["added"] == []


def test_added_centre_is_detected():
    records = _panel("S. aureus", 2022, ["RC1", "RC2"]) + _panel(
        "S. aureus", 2024, ["RC1", "RC2", "RC9"]
    )
    changes = detect_rc_panel_changes(records)
    assert changes[0]["added"] == ["RC9"]
    assert changes[0]["dropped"] == []


def test_baseline_is_the_earliest_edition_not_the_previous_one():
    # 2022 -> 2023 identical, 2024 drops RC2. The 2024 change is measured
    # against 2022 (the baseline), and 2023 (identical to baseline) is silent.
    records = (
        _panel("S. aureus", 2022, ["RC1", "RC2"])
        + _panel("S. aureus", 2023, ["RC1", "RC2"])
        + _panel("S. aureus", 2024, ["RC1"])
    )
    changes = detect_rc_panel_changes(records)
    assert [c["edition"] for c in changes] == [2024]
    assert changes[0]["baseline_edition"] == 2022
    assert changes[0]["dropped"] == ["RC2"]


def test_flag_is_applied_to_every_row_of_the_changed_edition_only():
    records = (
        _panel("E. coli", 2023, ["RC1", "RC2", "RC15"])
        + _panel("E. coli", 2024, ["RC1", "RC2"])
    )
    apply_rc_panel_flags(records)
    for r in records:
        changed = r.source_report_year == 2024
        has_flag = any(f.startswith("rc_panel_changed(") for f in r.flags)
        assert has_flag == changed
        if has_flag:
            assert "dropped=[RC15]" in r.flags[-1]
            assert "baseline=2023" in r.flags[-1]


def test_flag_is_idempotent():
    records = _panel("E. coli", 2023, ["RC1", "RC2"]) + _panel(
        "E. coli", 2024, ["RC1"]
    )
    apply_rc_panel_flags(records)
    apply_rc_panel_flags(records)
    flagged = [r for r in records if r.source_report_year == 2024]
    assert all(
        sum(f.startswith("rc_panel_changed(") for f in r.flags) == 1 for r in flagged
    )


def test_panel_by_edition_sorts_centres_numerically():
    records = _panel("E. coli", 2024, ["RC2", "RC10", "RC1"])
    panel = rc_panel_by_edition(records)
    assert panel["E. coli"][2024] == ["RC1", "RC2", "RC10"]


def test_single_edition_organism_has_no_panel_change():
    records = _panel("S. aureus", 2022, ["RC1", "RC2", "RC3"])
    assert detect_rc_panel_changes(records) == []


# --- cross-edition revisions: structurally near-empty -----------------------


def test_no_revision_when_each_edition_covers_only_its_own_year():
    # This is the real shape of the RC data: 2023 edition reports year 2023,
    # 2024 edition reports year 2024. Nothing to compare.
    records = [
        rc("E. coli", "RC1", "meropenem", 2023, n=50, tested=100, pct=50.0),
        rc("E. coli", "RC1", "meropenem", 2024, n=40, tested=100, pct=40.0),
    ]
    assert find_rc_cross_report_revisions(records) == []


def test_revision_detected_only_if_two_editions_ever_reported_the_same_year():
    # Hypothetical: if a future edition ever republished a prior year's RC
    # table with revised counts, the guard should fire.
    a = rc("E. coli", "RC1", "meropenem", 2023, n=50, tested=100, pct=50.0)
    b = rc("E. coli", "RC1", "meropenem", 2024, n=48, tested=100, pct=48.0)
    b.year = 2023  # same measurement year, different edition
    revs = find_rc_cross_report_revisions([a, b])
    assert len(revs) == 1
    assert revs[0]["kind"] == "count_revision"
