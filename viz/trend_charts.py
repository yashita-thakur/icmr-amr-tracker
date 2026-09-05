"""Trend charts for the README (spec section 6).

One chart per organism: susceptibility % by year, one line per antibiotic.
Every figure carries the attribution line required by spec section 7.

By default each (organism, antibiotic, year) point is taken from the most
recent report edition that reports it, since later editions supersede earlier
ones. `--revisions` additionally draws a chart showing where editions disagree.

The V2 Regional Centre dataset gets the same treatment: one chart per organism
that has an RC-wise table, susceptibility % by Regional Centre for that
organism's most recent RC edition, one line per antibiotic. The RC-wise tables
carry no year axis, so these are single-edition cross-sections, not trends.

V3 adds five NCDC NARS-Net figures, static only -- no companion JSON, the same
choice V2 made for the RC charts:

    narsnet_<organism>.png                % resistant by specimen, 8 editions
    narsnet_comparability_<organism>.png  which network reports what
    narsnet_surveillance_volume.png       isolates tested, both networks

The first two are NARS-Net alone. NARS-Net publishes % resistant and AMRSN
publishes % susceptible, and AMRSN publishes no % intermediate for either
organism, so an AMRSN % resistant cannot be computed and the two metrics can
never share an axis or a value. No figure here draws them together, and no
figure draws them side by side either: a reader seeing 77% resistant beside 21%
susceptible will subtract, and the answer would be wrong.

The volume figure is the single exception, and only because it plots counts. An
isolate tested is the same unit on both sides in a way the percentages are not.

Usage:
    python viz/trend_charts.py
    python viz/trend_charts.py --revisions
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import (  # noqa: E402
    FuncFormatter,
    LogLocator,
    MaxNLocator,
    NullLocator,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.sources import ATTRIBUTION, PROCESSED_DIR  # noqa: E402

FIGURES_DIR = REPO_ROOT / "docs" / "figures"

# Carbapenems drawn solid, everything else dashed, so the clinically critical
# lines read first.
CARBAPENEMS = {"meropenem", "imipenem", "ertapenem"}


def load_rows():
    csv_path = PROCESSED_DIR / "amr_trends.csv"
    if not csv_path.exists():
        raise SystemExit(
            "{} not found. Run `python -m src.build_dataset` first.".format(csv_path)
        )
    with open(csv_path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_rc_rows():
    csv_path = PROCESSED_DIR / "amr_rc_trends.csv"
    if not csv_path.exists():
        raise SystemExit(
            "{} not found. Run `python -m src.build_rc_dataset` first.".format(csv_path)
        )
    with open(csv_path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# Minimum isolates tested before a point is drawn. ICMR itself asterisks its
# very small cells and prints "(-)" rather than a percentage for them; a
# proportion from one or eight isolates is noise, and plotting it as a trend
# point invites exactly the misreading this project exists to avoid. Cefazolin
# is the case in point: it is tested against a handful of isolates a year, and
# charting it produces a line that swings between 0% and 44% while meaning
# nothing.
MIN_TESTED_FOR_CHART = 30


def latest_edition_series(rows):
    """Collapse to one value per (organism, antibiotic, year), preferring the
    most recent report edition.

    Points the source did not publish a percentage for, flagged as low-count,
    or resting on fewer than `MIN_TESTED_FOR_CHART` isolates are not charted.
    They remain in the dataset -- this filter is presentational only.
    """
    best = {}
    for r in rows:
        flags = r.get("flags") or ""
        if not r["susceptible_pct"]:
            continue
        if "low_isolate_count_asterisk" in flags:
            continue
        # Colistin in the non-fermenter tables is INTERMEDIATE susceptibility,
        # not susceptibility (both tables footnote this). Drawn on the same
        # axes it would show colistin around 97% while meropenem sits at 9%,
        # reading unmistakably as "colistin still works" -- a different claim
        # from the one the source makes. Excluded from the charts; still in the
        # dataset, flagged.
        if "colistin_is_intermediate_susceptibility" in flags:
            continue
        try:
            if int(r["tested_n"]) < MIN_TESTED_FOR_CHART:
                continue
        except (TypeError, ValueError):
            continue
        key = (r["organism"], r["antibiotic"], int(r["year"]))
        srp = int(r["source_report_year"])
        if key not in best or srp > best[key][0]:
            best[key] = (srp, float(r["susceptible_pct"]))
    return {k: v[1] for k, v in best.items()}


def export_chart_data(rows, series, out_path):
    """Write the compact series the interactive charts read.

    Deliberately derived from `latest_edition_series` -- the same function the
    PNGs use -- so the static and interactive renderings cannot drift apart.
    Two rendering paths are only safe while they share one source of truth.

    The full dataset is ~600 KB; the page needs only (drug, year, percentage),
    which is a small fraction of that.
    """
    by_org: dict = {}
    for (organism, antibiotic, year), pct in series.items():
        by_org.setdefault(organism, {}).setdefault(antibiotic, []).append([year, pct])

    organisms = []
    for organism in sorted(by_org):
        drugs = []
        for antibiotic in sorted(by_org[organism]):
            points = sorted(by_org[organism][antibiotic])
            if len(points) < 2:
                continue
            drugs.append(
                {
                    "drug": antibiotic,
                    "carbapenem": antibiotic in CARBAPENEMS,
                    "points": [[y, round(v, 2)] for y, v in points],
                }
            )
        if drugs:
            organisms.append(
                {
                    "name": organism,
                    "slug": organism.lower().replace(" ", "_").replace(".", ""),
                    "series": drugs,
                }
            )

    years = sorted({y for (_o, _a, y) in series})
    payload = {
        "attribution": ATTRIBUTION,
        "min_tested": MIN_TESTED_FOR_CHART,
        "excluded": (
            "Points with fewer than {} isolates tested, points where the "
            "source does not print a percentage, and colistin in the "
            "non-fermenter tables (reported as intermediate susceptibility) "
            "are not plotted.".format(MIN_TESTED_FOR_CHART)
        ),
        "years": years,
        "organisms": organisms,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"))
    return out_path


def _footer(fig, extra=""):
    fig.text(
        0.5,
        0.015,
        (extra + "\n" if extra else "") + ATTRIBUTION,
        ha="center",
        va="bottom",
        fontsize=7,
        color="#555555",
        wrap=True,
    )


def chart_organism(series, organism, out_path):
    abx = sorted({a for (o, a, _y) in series if o == organism})
    if not abx:
        return None

    fig, ax = plt.subplots(figsize=(9, 5.5))
    cmap = plt.get_cmap("tab10")
    for i, antibiotic in enumerate(abx):
        pts = sorted(
            (y, v) for (o, a, y), v in series.items() if o == organism and a == antibiotic
        )
        if len(pts) < 2:
            continue
        years = [p[0] for p in pts]
        vals = [p[1] for p in pts]
        ax.plot(
            years,
            vals,
            marker="o",
            markersize=4,
            linewidth=2.0 if antibiotic in CARBAPENEMS else 1.3,
            linestyle="-" if antibiotic in CARBAPENEMS else "--",
            color=cmap(i % 10),
            label=antibiotic,
        )

    ax.set_title(
        "{}: national susceptibility trend".format(organism),
        fontsize=13,
        style="italic",
    )
    ax.set_xlabel("Year")
    ax.set_ylabel("% susceptible")
    ax.set_ylim(0, 100)
    ax.grid(alpha=0.25, linestyle=":")
    ax.legend(
        fontsize=8, ncol=2, loc="upper right", frameon=True, title="Antibiotic"
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    _footer(
        fig,
        "Carbapenems shown as solid lines. Not plotted: points with fewer than "
        "{} isolates tested, points where the source does not print a "
        "percentage, and colistin in the non-fermenter tables (reported as "
        "intermediate susceptibility, not susceptibility).".format(MIN_TESTED_FOR_CHART),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def rc_editions(rc_rows, organism):
    """Report years that carry an RC-wise table for this organism, oldest first."""
    return sorted(
        {int(r["source_report_year"]) for r in rc_rows if r["organism"] == organism}
    )


def rc_baseline_panel(rc_rows, organism):
    """The RC set from this organism's earliest RC edition, in RC-number order.

    This is the x-axis every RC chart for the organism is drawn against, so that
    a Regional Centre a later edition stopped reporting still occupies its slot
    on the axis instead of silently vanishing.
    """
    base = rc_editions(rc_rows, organism)[0]
    rcs = {
        r["regional_centre"]
        for r in rc_rows
        if r["organism"] == organism and int(r["source_report_year"]) == base
    }
    return sorted(rcs, key=lambda s: int(s[2:]))


def latest_rc_cross_section(rc_rows, organism):
    """From the most recent RC edition: the RC set the table actually printed,
    and one susceptibility value per (regional_centre, antibiotic).

    Same presentational filter as `latest_edition_series`: points the source did
    not print a percentage for, marked low-count, or resting on fewer than
    `MIN_TESTED_FOR_CHART` isolates are not charted, and `pct_mismatch` cells --
    where the printed percentage does not reconcile with its own counts -- are
    dropped here too, the same way suppressed percentages are. They remain in the
    dataset; this filter is presentational only.

    The RC set is taken before that filter, so a Regional Centre the edition did
    print but only with tiny denominators is not mistaken for one the edition
    dropped from its panel.
    """
    latest = rc_editions(rc_rows, organism)[-1]
    edition_panel = set()
    values = {}
    for r in rc_rows:
        if r["organism"] != organism or int(r["source_report_year"]) != latest:
            continue
        edition_panel.add(r["regional_centre"])
        flags = r.get("flags") or ""
        if not r["susceptible_pct"]:
            continue
        if "low_isolate_count_asterisk" in flags:
            continue
        if "pct_mismatch" in flags:
            continue
        try:
            if int(r["tested_n"]) < MIN_TESTED_FOR_CHART:
                continue
        except (TypeError, ValueError):
            continue
        values[(r["regional_centre"], r["antibiotic"])] = float(r["susceptible_pct"])
    return latest, edition_panel, values


def chart_organism_rc(rc_rows, organism, out_path):
    edition, edition_panel, values = latest_rc_cross_section(rc_rows, organism)
    abx = sorted({a for (_rc, a) in values})
    if not abx:
        return None

    panel = rc_baseline_panel(rc_rows, organism)
    dropped = [rc for rc in panel if rc not in edition_panel]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    cmap = plt.get_cmap("tab10")
    xs = list(range(len(panel)))
    for i, antibiotic in enumerate(abx):
        # A Regional Centre absent from this edition -- or a cell the filter
        # above removed -- leaves a gap the line breaks across, rather than
        # bridging two RCs that were never adjacent measurements. The RC keeps
        # its slot on the axis, so the break is visible.
        vals = [values.get((rc, antibiotic), float("nan")) for rc in panel]
        if sum(1 for v in vals if v == v) < 2:
            continue
        ax.plot(
            xs,
            vals,
            marker="o",
            markersize=4,
            linewidth=2.0 if antibiotic in CARBAPENEMS else 1.3,
            linestyle="-" if antibiotic in CARBAPENEMS else "--",
            color=cmap(i % 10),
            label=antibiotic,
        )

    ax.set_title(
        "{}: susceptibility by Regional Centre".format(organism),
        fontsize=13,
        style="italic",
    )
    ax.set_xlabel("Regional Centre")
    ax.set_ylabel("% susceptible")
    ax.set_ylim(0, 100)
    ax.set_xticks(xs)
    ax.set_xticklabels([rc[2:] for rc in panel], fontsize=8)
    ax.grid(alpha=0.25, linestyle=":")
    ax.legend(
        fontsize=8, ncol=2, loc="upper right", frameon=True, title="Antibiotic"
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    dropped_note = (
        " RC {} not in this edition's panel.".format(", ".join(rc[2:] for rc in dropped))
        if dropped
        else ""
    )
    _footer(
        fig,
        "{} edition; these RC-wise tables have no year axis. Carbapenems shown "
        "as solid lines. Not plotted: points with fewer than {} isolates "
        "tested, points where the source does not print a percentage, and cells "
        "flagged pct_mismatch.{}".format(edition, MIN_TESTED_FOR_CHART, dropped_note),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def chart_revisions(out_path, top_n=12):
    """Show where different report editions disagree about the same year.

    Charts the quantity that actually moved. A revision can change the
    denominator while leaving the printed percentage untouched (E. coli /
    piperacillin-tazobactam / 2022 goes from 5170/14729 to 5170/14728, still
    35.1%), so plotting percentages alone would show nothing at all.
    """
    rev_path = PROCESSED_DIR / "revisions.json"
    if not rev_path.exists():
        return None
    with open(rev_path, encoding="utf-8") as fh:
        revisions = json.load(fh).get("revisions", [])
    if not revisions:
        return None

    panels = []
    counts = [r for r in revisions if r["kind"] == "count_revision"][:top_n]
    pctrev = [r for r in revisions if r["kind"] == "percentage_revision"][:top_n]
    if counts:
        panels.append(("tested_n_by_report", counts, "Isolates tested (N)"))
    if pctrev:
        panels.append(("susceptible_pct_by_report", pctrev, "% susceptible"))
    if not panels:
        return None

    heights = [max(1.4, 0.5 * len(items) + 1.2) for _k, items, _x in panels]
    fig, axes = plt.subplots(
        len(panels), 1, figsize=(9, sum(heights) + 1.6), squeeze=False
    )

    for ax, (key, items, xlabel) in zip(axes[:, 0], panels):
        labels = []
        is_count = key.startswith("tested_n")
        for i, rev in enumerate(items):
            by_report = {int(k): v for k, v in rev[key].items() if v is not None}
            if not by_report:
                continue
            vals = list(by_report.values())
            ax.plot(
                [min(vals), max(vals)], [i, i], color="#bbbbbb", linewidth=2, zorder=1
            )

            # Editions that agree land on the same x. Draw ONE marker per
            # distinct value and name the editions that share it, rather than
            # stacking markers so that all but the last become invisible.
            shared = {}
            for edition, value in sorted(by_report.items()):
                shared.setdefault(value, []).append(edition)
            for value, editions in sorted(shared.items()):
                ax.scatter(value, i, s=70, zorder=2, color="#2c6fb5")
                fmt = "{:,.0f}" if is_count else "{:g}"
                ax.annotate(
                    "{}\n{}".format(
                        fmt.format(value),
                        ", ".join(str(e) for e in editions),
                    ),
                    (value, i),
                    textcoords="offset points",
                    xytext=(0, 10),
                    ha="center",
                    fontsize=7,
                    linespacing=1.3,
                )
            org = rev["organism"]
            labels.append(
                "{}. {} {} ({})".format(
                    org.split()[0][0], org.split()[-1], rev["antibiotic"], rev["year"]
                )
            )

        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_ylim(-0.9, max(len(labels) - 0.3, 0.9))
        ax.invert_yaxis()
        ax.set_xlabel("{}  (labelled with the report editions reporting it)".format(
            xlabel
        ))
        ax.margins(x=0.25)
        ax.grid(axis="x", alpha=0.25, linestyle=":")
        # Integer counts must not be rendered as "8.0 +1.472e4", nor given
        # fractional ticks -- there is no such thing as 14,728.2 isolates.
        ax.ticklabel_format(style="plain", axis="x", useOffset=False)
        if is_count:
            ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
            ax.xaxis.set_major_formatter(
                FuncFormatter(lambda v, _pos: "{:,.0f}".format(v))
            )

    axes[0, 0].set_title(
        "Same year, different report edition, different number", fontsize=12
    )
    fig.tight_layout(rect=(0, 0.11, 1, 1))
    _footer(
        fig,
        "Each row is one organism/antibiotic/year reported differently by two "
        "ICMR editions.\nThis reflects revision in the source reports, not "
        "extraction error.",
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------------
# V3 -- NCDC NARS-Net, carried as a parallel series
#
# NARS-Net publishes % RESISTANT; AMRSN publishes % SUSCEPTIBLE. On these
# figures high is bad; on every AMRSN figure above, high is good. AMRSN
# publishes no % intermediate for either organism, so an AMRSN % resistant
# cannot be computed and the two metrics can never share an axis or a value.
# The NARS-Net figures therefore stand alone, use a different colour family so
# they do not read as a continuation of the AMRSN set, and say "% resistant"
# in the title, the axis label and the footer.
#
# The one exception is the surveillance-volume figure, which puts both networks
# on one axis on purpose: it plots isolate counts, and a count is the same unit
# on both sides in a way the two percentages are not.
# ---------------------------------------------------------------------------

NARSNET_CMAP = "Dark2"  # deliberately not tab10 -- see above


def load_narsnet_rows():
    csv_path = PROCESSED_DIR / "narsnet_trends.csv"
    if not csv_path.exists():
        raise SystemExit(
            "{} not found. Run `python -m src.build_narsnet_dataset` first.".format(
                csv_path
            )
        )
    with open(csv_path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_comparability():
    path = PROCESSED_DIR / "comparability_matrix.json"
    if not path.exists():
        raise SystemExit(
            "{} not found. Run `python -m src.build_comparability` first.".format(path)
        )
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def shared_antibiotics(matrix, organism):
    """Drugs both networks report somewhere in the series, from the matrix.

    Taken from the matrix rather than recomputed here, so the trend figures and
    the comparability figures cannot disagree about what "shared" means.
    """
    for entry in matrix["summary"]["by_organism"]:
        if entry["organism"] == organism:
            return entry["antibiotics_both_networks_report"]
    return []


# The specimen columns each organism's figure is drawn on: the only columns
# with an unbroken run across all eight editions. Blood qualifies for both
# organisms and urine for E. coli; every other column is either a composite
# whose membership changes between editions or one that begins in 2021, and
# plotting either as a continuous line would join measurements of different
# things. S. aureus is never surveilled from urine.
NARSNET_PANELS = {
    "Escherichia coli": ["blood", "urine"],
    "Staphylococcus aureus": ["blood"],
}

# The edition where the panels widen: E. coli 9 drugs -> 17, S. aureus 8 -> 9.
# Marked so that a line starting mid-chart reads as the panel changing rather
# than as missing data.
NARSNET_PANEL_WIDENED = 2021


def narsnet_series(rows, organism, specimen, antibiotics=None):
    """(antibiotic, year) -> printed % resistant, for one specimen column.

    Same presentational filter as `latest_edition_series` -- no percentage
    printed, or fewer than `MIN_TESTED_FOR_CHART` isolates tested, and the
    point is not drawn -- with one deliberate difference from the RC charts.

    Cells flagged `pct_mismatch` ARE plotted here. That flag records a
    disagreement between a printed percentage and the numerator printed beside
    it, and these charts draw the percentage, which is the figure the source's
    own chapters restate. The RC charts drop such cells because there the
    printed percentage is the thing in doubt (0% against counts of 2/3); here
    it is the numerator, and seven of the eight NARS-Net cases differ from
    their own counts by under 0.54 percentage points. Dropping them would open
    a one-year gap in a line over a rounding difference.
    """
    wanted = set(antibiotics) if antibiotics else None
    out = {}
    for r in rows:
        if r["organism"] != organism or r["specimen"] != specimen:
            continue
        if wanted is not None and r["antibiotic"] not in wanted:
            continue
        if not r["resistant_pct"]:
            continue
        try:
            if int(r["tested_n"]) < MIN_TESTED_FOR_CHART:
                continue
        except (TypeError, ValueError):
            continue
        out[(r["antibiotic"], int(r["year"]))] = float(r["resistant_pct"])
    return out


def chart_narsnet_organism(rows, matrix, organism, out_path):
    specimens = NARSNET_PANELS[organism]
    abx = shared_antibiotics(matrix, organism)
    panels = [(s, narsnet_series(rows, organism, s, abx)) for s in specimens]
    panels = [(s, v) for s, v in panels if v]
    if not panels:
        return None

    # Laid out in inches. The footer runs to several lines and is the same
    # length whether there are one panel or two, so it needs a fixed allowance
    # rather than a fraction of a figure whose height changes with the organism.
    fig_w, panel_h = 9.0, 3.1
    left, right, top, bottom = 0.85, 0.25, 1.40, 1.70
    fig_h = top + panel_h * len(panels) + bottom
    fig, axes = plt.subplots(
        len(panels), 1, figsize=(fig_w, fig_h), squeeze=False, sharex=True
    )
    fig.subplots_adjust(
        left=left / fig_w,
        right=1 - right / fig_w,
        top=1 - top / fig_h,
        bottom=bottom / fig_h,
        hspace=0.22,
    )
    cmap = plt.get_cmap(NARSNET_CMAP)
    drawn = set()
    for ax, (specimen, series) in zip(axes[:, 0], panels):
        for i, antibiotic in enumerate(abx):
            pts = sorted(
                (y, v) for (a, y), v in series.items() if a == antibiotic
            )
            # A drug the source prints in one edition only cannot be drawn as
            # a trend. E. coli ceftazidime (2017) and S. aureus vancomycin
            # (2018) are each in a single NARS-Net table and drop out here.
            if len(pts) < 2:
                continue
            drawn.add(antibiotic)
            ax.plot(
                [p[0] for p in pts],
                [p[1] for p in pts],
                marker="o",
                markersize=4,
                linewidth=2.0 if antibiotic in CARBAPENEMS else 1.3,
                linestyle="-" if antibiotic in CARBAPENEMS else "--",
                color=cmap(i % 8),
                label=antibiotic,
            )
        ax.axvline(
            NARSNET_PANEL_WIDENED - 0.5, color="#999999", linewidth=1, linestyle=":"
        )
        ax.annotate(
            "panel widens",
            (NARSNET_PANEL_WIDENED - 0.5, 99),
            textcoords="offset points",
            xytext=(4, -2),
            va="top",
            fontsize=7,
            color="#777777",
        )
        ax.set_title(
            "{} isolates".format(specimen.replace("_", " ")),
            fontsize=10,
            loc="left",
            color="#444444",
        )
        ax.set_ylabel("% resistant")
        ax.set_ylim(0, 100)
        ax.grid(alpha=0.25, linestyle=":")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))

    axes[-1, 0].set_xlabel("Year")
    # In the margin, not on the axes. Seven or eight lines spread over most of
    # a 0-100 panel leave no corner genuinely free, and a legend placed in the
    # least-bad one still hides a line -- on the E. coli blood panel it sat on
    # imipenem for four of its eight years.
    fig.legend(
        *axes[0, 0].get_legend_handles_labels(),
        fontsize=8,
        ncol=4,
        loc="upper center",
        bbox_to_anchor=(0.5, 1 - 0.46 / fig_h),
        frameon=False,
        title="Antibiotic",
    )
    fig.suptitle(
        "{}: NARS-Net % RESISTANT, by specimen".format(organism),
        fontsize=13,
        style="italic",
        y=1 - 0.24 / fig_h,
    )
    missing = [a for a in abx if a not in drawn]
    _footer(
        fig,
        "NCDC NARS-Net, all eight editions 2017-2024. HIGH IS BAD HERE: this is "
        "% resistant, not the % susceptible the ICMR-AMRSN figures above show, "
        "and the two are not two views of one number -- AMRSN publishes no "
        "% intermediate for this organism, so its % resistant cannot be "
        "computed. Of the {} drugs both networks report, {} are drawn{}; the "
        "other drugs in NARS-Net's panel are in the dataset. Carbapenems shown "
        "as solid lines. Not plotted: points with fewer than {} isolates "
        "tested and points where the source prints no percentage. Cells "
        "flagged pct_mismatch ARE plotted: that flag records a printed "
        "percentage disagreeing with the numerator printed beside it, and it "
        "is the percentage these charts draw.".format(
            len(abx),
            len(drawn),
            (
                ", and {} is left out because NARS-Net prints it in one "
                "edition only, which is not a trend".format(", ".join(missing))
                if missing
                else ""
            ),
            MIN_TESTED_FOR_CHART,
        ),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# Colour and glyph per coverage state. The glyph is not decoration: it carries
# the same information as the colour, so the matrix survives greyscale
# printing and does not rely on telling green from orange.
COVERAGE_STYLE = {
    "both": ("#4d7c5f", "B"),
    "narsnet_only": ("#d9822b", "N"),
    "amrsn_only": ("#6a8caf", "A"),
    "neither": ("#ededed", ""),
}


def _specimen_rows(cells, organism):
    """Rows for the specimen strip: which basis each network printed, per year.

    Returns (label, {year: True/False}, colour) tuples -- the NARS-Net specimen
    columns that organism's editions print, then one row for AMRSN's own basis.
    """
    years = sorted({c["year"] for c in cells})
    narsnet_by_year: dict = {}
    amrsn_years = set()
    basis = None
    for cell in cells:
        if cell["narsnet"]:
            for specimen in cell["narsnet"]["specimen_basis"]:
                narsnet_by_year.setdefault(specimen, set()).add(cell["year"])
        if cell["amrsn"]:
            amrsn_years.add(cell["year"])
            basis = cell["amrsn"]["specimen_basis"]

    def sort_key(specimen):
        # Composites last, then alphabetical, so the 2021 split reads as a
        # block of composite rows ending where the single-stratum rows begin.
        return ("+" in specimen, specimen)

    rows = [
        (
            specimen.replace("_", " ").replace("osbf", "OSBF"),
            {y: y in narsnet_by_year[specimen] for y in years},
            COVERAGE_STYLE["narsnet_only"][0],
        )
        for specimen in sorted(narsnet_by_year, key=sort_key)
    ]
    if basis:
        # The caption wording itself is too long for a row label and is given
        # in the footer instead; AMRSN prints one pooled column either way.
        rows.append(
            (
                "AMRSN (one pooled column)",
                {y: y in amrsn_years for y in years},
                COVERAGE_STYLE["amrsn_only"][0],
            )
        )
    return rows, basis


def chart_comparability(matrix, organism, out_path):
    """One cell per antibiotic x year: which network reports it, on which
    metric, from which specimen basis.

    The matrix says nothing whatever about whether two reported figures agree,
    and cannot: the networks share no comparison value. A "both" cell means
    both networks print that combination, and that is all it means.
    """
    cells = [c for c in matrix["matrix"] if c["organism"] == organism]
    if not cells:
        return None
    drugs = sorted({c["antibiotic"] for c in cells})
    years = sorted({c["year"] for c in cells})
    by_key = {(c["antibiotic"], c["year"]): c for c in cells}
    strip, amrsn_basis = _specimen_rows(cells, organism)

    # Laid out in inches rather than by tight_layout, which cannot measure a
    # grid drawn as patches and clips the longest row labels when it tries.
    fig_w, grid_h, strip_h = 9.0, 0.30 * len(drugs), 0.30 * len(strip)
    left, right, top, gap, bottom = 2.15, 0.25, 1.45, 0.68, 2.00
    fig_h = top + grid_h + gap + strip_h + bottom
    fig, (ax, ax_strip) = plt.subplots(
        2, 1, figsize=(fig_w, fig_h), gridspec_kw={"height_ratios": [grid_h, strip_h]}
    )
    fig.subplots_adjust(
        left=left / fig_w,
        right=1 - right / fig_w,
        top=1 - top / fig_h,
        bottom=bottom / fig_h,
        hspace=gap / ((grid_h + strip_h) / 2),
    )

    for row, drug in enumerate(drugs):
        for col, year in enumerate(years):
            colour, glyph = COVERAGE_STYLE[by_key[(drug, year)]["coverage"]]
            ax.add_patch(
                plt.Rectangle(
                    (col, row), 1, 1, facecolor=colour, edgecolor="white", linewidth=1.2
                )
            )
            if glyph:
                ax.text(
                    col + 0.5,
                    row + 0.5,
                    glyph,
                    ha="center",
                    va="center",
                    fontsize=7.5,
                    color="white",
                    fontweight="bold",
                )
    _grid_axes(ax, years, drugs)
    fig.suptitle(
        "{}: which network reports what".format(organism),
        fontsize=13,
        style="italic",
        y=1 - 0.42 / fig_h,
    )

    for row, (label, present, colour) in enumerate(strip):
        for col, year in enumerate(years):
            ax_strip.add_patch(
                plt.Rectangle(
                    (col, row),
                    1,
                    1,
                    facecolor=colour if present[year] else COVERAGE_STYLE["neither"][0],
                    edgecolor="white",
                    linewidth=1.2,
                )
            )
    _grid_axes(ax_strip, years, [label for label, _p, _c in strip])
    ax_strip.set_title(
        "specimen basis each network prints", fontsize=9, loc="left", color="#444444"
    )
    ax_strip.set_xlabel("Year")

    handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=colour, edgecolor="white")
        for colour, _g in COVERAGE_STYLE.values()
    ]
    labels = [
        "B  both networks report it",
        "N  NARS-Net only (% resistant)",
        "A  AMRSN only (% susceptible)",
        "    neither reports it",
    ]
    ax.legend(
        handles,
        labels,
        fontsize=8,
        ncol=2,
        loc="lower left",
        bbox_to_anchor=(0, 1.06),
        frameon=False,
    )

    counts = _coverage_counts(cells)
    shared = sorted({c["antibiotic"] for c in cells if c["amrsn"]} &
                    {c["antibiotic"] for c in cells if c["narsnet"]})
    both_years = {
        d: [y for y in years if by_key[(d, y)]["coverage"] == "both"] for d in shared
    }
    both_every_year = [d for d in shared if len(both_years[d]) == len(years)]
    partial = [d for d in shared if d not in both_every_year]
    # The organism's own sharpest case, found rather than named: the shared
    # drug that actually overlaps in the fewest years. E. coli ceftazidime and
    # S. aureus vancomycin are each in one NARS-Net table only.
    sharpest = min(partial, key=lambda d: (len(both_years[d]), d)) if partial else None
    _footer(
        fig,
        "{} drugs x {} years = {} cells: {} reported by both networks, {} by "
        "NARS-Net only, {} by AMRSN only, {} by neither.\n"
        "PANEL-LEVEL OVERLAP IS NOT CELL-LEVEL OVERLAP. {} of the {} drugs "
        "both networks report are reported by both in every year; {} "
        "{}.{}\n"
        "A 'both' cell means both networks print that combination. It does NOT "
        "mean the two figures are comparable: NARS-Net prints % resistant and "
        "AMRSN % susceptible, and AMRSN publishes no % intermediate for these "
        "organisms, so its % resistant cannot be computed. Take each value "
        "from its own dataset. The specimen bases are not equivalent either: "
        "AMRSN's one pooled column is captioned '{}', NARS-Net prints a column "
        "per specimen, and no NARS-Net column from 2021 has the same "
        "membership as any earlier one.".format(
            len(drugs),
            len(years),
            len(cells),
            counts["both"],
            counts["narsnet_only"],
            counts["amrsn_only"],
            counts["neither"],
            len(both_every_year),
            len(shared),
            len(partial),
            "overlap in some years only" if partial else "overlap in none",
            (
                " {} is the sharp case: it counts as a drug both networks "
                "report on {} of its {} cells ({}).".format(
                    sharpest,
                    len(both_years[sharpest]),
                    len(years),
                    ", ".join(str(y) for y in both_years[sharpest]),
                )
                if sharpest
                else ""
            ),
            amrsn_basis,
        ),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def _grid_axes(ax, years, row_labels):
    ax.set_xlim(0, len(years))
    ax.set_ylim(0, len(row_labels))
    ax.set_xticks([i + 0.5 for i in range(len(years))])
    ax.set_xticklabels([str(y) for y in years], fontsize=8)
    ax.set_yticks([i + 0.5 for i in range(len(row_labels))])
    ax.set_yticklabels(row_labels, fontsize=8)
    ax.invert_yaxis()
    ax.tick_params(length=0)
    for side in ax.spines.values():
        side.set_visible(False)


def _coverage_counts(cells):
    counts = {state: 0 for state in COVERAGE_STYLE}
    for cell in cells:
        counts[cell["coverage"]] += 1
    return counts


def _constituents(specimen):
    return frozenset(specimen.split("+"))


def _best_disjoint_total(printed):
    """Largest all-specimen denominator recoverable from one drug-year's columns.

    `printed` maps specimen column -> isolates tested. Columns overlap: an
    edition can print blood, urine and a pooled Blood+Urine+PA+OSBF column
    covering both. Summing everything would double-count, and summing only the
    single strata would understate any year whose pooled column is the sole
    place a stratum appears. So: take the pairwise-disjoint subset covering the
    most strata, preferring the one printed as fewest columns -- which means a
    pooled column is used as printed where one exists, and the strata are
    summed where none does.
    """
    columns = sorted(printed)
    best = None
    for mask in range(1, 1 << len(columns)):
        chosen = [columns[i] for i in range(len(columns)) if mask >> i & 1]
        covered: set = set()
        for specimen in chosen:
            parts = _constituents(specimen)
            if parts & covered:
                break
            covered |= parts
        else:
            key = (len(covered), -len(chosen))
            if best is None or key > best[0]:
                best = (key, sum(printed[s] for s in chosen))
    return best[1] if best else None


def narsnet_volume(rows, organism, specimen=None):
    """year -> the largest number of isolates any one drug was tested against.

    With `specimen`, that column alone. Without, every specimen the edition
    prints, combined by `_best_disjoint_total` so nothing is double-counted.

    A per-drug denominator, not an isolate count: neither network publishes
    "isolates tested" for an organism, only "isolates tested against this
    drug", and those differ widely inside one year. The maximum is the
    best-supported lower bound on how many isolates the year's panel reached.
    """
    per_drug: dict = {}
    for r in rows:
        if r["organism"] != organism:
            continue
        if specimen is not None and r["specimen"] != specimen:
            continue
        try:
            tested = int(r["tested_n"])
        except (TypeError, ValueError):
            continue
        per_drug.setdefault((int(r["year"]), r["antibiotic"]), {})[r["specimen"]] = tested

    out: dict = {}
    for (year, _drug), printed in per_drug.items():
        total = (
            printed[specimen] if specimen is not None else _best_disjoint_total(printed)
        )
        if total is None:
            continue
        out[year] = max(out.get(year, 0), total)
    return out


def amrsn_volume(rows, organism):
    """year -> largest printed denominator, from the most recent edition to
    report that year. Same rule as `latest_edition_series` for which edition
    wins, so the figure and the AMRSN trend charts quote the same numbers."""
    best: dict = {}
    for r in rows:
        if r["organism"] != organism:
            continue
        try:
            tested = int(r["tested_n"])
        except (TypeError, ValueError):
            continue
        year, edition = int(r["year"]), int(r["source_report_year"])
        if year not in best or edition > best[year][0]:
            best[year] = (edition, tested)
        elif edition == best[year][0]:
            best[year] = (edition, max(best[year][1], tested))
    return {y: v for y, (_e, v) in best.items()}


def _spread(rows, organism, year, specimen=None, edition=None):
    """min and max printed denominator across one year's panel, for the footer."""
    vals = []
    for r in rows:
        if r["organism"] != organism or int(r["year"]) != year:
            continue
        if specimen is not None and r.get("specimen") != specimen:
            continue
        if edition is not None and int(r["source_report_year"]) != edition:
            continue
        try:
            vals.append(int(r["tested_n"]))
        except (TypeError, ValueError):
            continue
    return (min(vals), max(vals)) if vals else (None, None)


def chart_surveillance_volume(amrsn_rows, narsnet_rows, out_path, organisms=None):
    """Isolates tested per year, both networks, on one count axis.

    THE ONE FIGURE IN V3 THAT PUTS THE TWO NETWORKS ON A SHARED AXIS, and it
    does so because a count is the same unit on both sides. The percentages are
    not: NARS-Net prints % resistant, AMRSN % susceptible, and no % intermediate
    is published for these organisms, so those two can never share an axis.
    """
    organisms = organisms or ["Escherichia coli", "Staphylococcus aureus"]
    fig, axes = plt.subplots(
        len(organisms), 1, figsize=(9, 3.6 * len(organisms) + 1.6), squeeze=False
    )

    for ax, organism in zip(axes[:, 0], organisms):
        blood = narsnet_volume(narsnet_rows, organism, specimen="blood")
        every = narsnet_volume(narsnet_rows, organism)
        amrsn = amrsn_volume(amrsn_rows, organism)
        for label, data, style in (
            ("NARS-Net, blood", blood, {"color": "#d9822b", "linestyle": "-"}),
            (
                "NARS-Net, every specimen printed",
                every,
                {"color": "#d9822b", "linestyle": ":"},
            ),
            ("AMRSN, as printed", amrsn, {"color": "#6a8caf", "linestyle": "-"}),
        ):
            pts = sorted(data.items())
            if len(pts) < 2:
                continue
            ax.plot(
                [p[0] for p in pts],
                [p[1] for p in pts],
                marker="o",
                markersize=4,
                linewidth=1.8,
                label=label,
                **style
            )
        ax.set_yscale("log")
        ax.set_ylabel("isolates tested (log)")
        ax.set_title(organism, fontsize=11, style="italic", loc="left")
        ax.grid(alpha=0.25, linestyle=":", which="both")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        # Ticks at 1/2/5 per decade, labelled as plain counts. Left to
        # matplotlib, one panel comes out reading "10,000" and the other
        # "2 x 10^4" -- two renderings of a count, on one figure.
        ax.yaxis.set_major_locator(LogLocator(base=10.0, subs=(1.0, 2.0, 5.0)))
        ax.yaxis.set_minor_locator(NullLocator())
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: "{:,.0f}".format(v)))
        ax.legend(fontsize=8, loc="lower right", frameon=True)

    axes[-1, 0].set_xlabel("Year")
    fig.suptitle(
        "Surveillance volume: the one metric the two networks share",
        fontsize=13,
    )
    fig.tight_layout(rect=(0, 0.15, 1, 0.97))

    ec_lo, ec_hi = _spread(narsnet_rows, "Escherichia coli", 2024, specimen="urine")
    am_lo, am_hi = _spread(amrsn_rows, "Escherichia coli", 2024, edition=2024)
    _footer(
        fig,
        "Counts, not percentages -- which is why this is the one figure here "
        "that puts both networks on one axis. An isolate tested is the same "
        "unit on both sides; the two resistance metrics are not, since "
        "NARS-Net prints % resistant, AMRSN % susceptible, and no "
        "% intermediate is published for these organisms.\n"
        "Each line is the LARGEST printed denominator in that year's panel. "
        "Neither network publishes 'isolates tested' for an organism -- only "
        "isolates tested against each drug -- and those differ widely within "
        "one year: E. coli urine in 2024 runs {:,}-{:,} across sixteen "
        "NARS-Net drugs, and the AMRSN 2024 panel runs {:,}-{:,} across ten. "
        "Log axis: equal vertical distance is equal proportional change, so "
        "what is comparable here is the TRAJECTORY, not the size.\n"
        "The two cover different populations. AMRSN prints one pooled column, "
        "captioned 'all samples (except faeces and urine)' for E. coli and "
        "'all samples' for S. aureus; NARS-Net prints a column per specimen "
        "and no pooled column at all from 2021, so its dotted line is combined "
        "here from the columns each edition prints. The AMRSN dip in 2023 is "
        "in the source and is not a revision: E. coli "
        "piperacillin-tazobactam runs 14,728 tested in 2022 to 7,559 in 2023 "
        "and 11,679 in 2024, and the 2023 and 2024 editions print the 2023 "
        "figure identically.".format(ec_lo, ec_hi, am_lo, am_hi),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--revisions", action="store_true", help="also draw revisions chart")
    args = ap.parse_args(argv)

    rows = load_rows()
    series = latest_edition_series(rows)
    organisms = sorted({o for (o, _a, _y) in series})

    written = [export_chart_data(rows, series, REPO_ROOT / "docs" / "data" / "trends.json")]
    for organism in organisms:
        slug = organism.lower().replace(" ", "_").replace(".", "")
        out = chart_organism(series, organism, FIGURES_DIR / "trend_{}.png".format(slug))
        if out:
            written.append(out)

    rc_rows = load_rc_rows()
    for organism in sorted({r["organism"] for r in rc_rows}):
        slug = organism.lower().replace(" ", "_").replace(".", "")
        out = chart_organism_rc(rc_rows, organism, FIGURES_DIR / "rc_{}.png".format(slug))
        if out:
            written.append(out)

    # V3 -- NARS-Net, drawn as its own series and never joined to the AMRSN
    # figures above. No companion JSON: these are static figures only, as the
    # V2 RC charts are. Two rendering paths are only safe while they share one
    # source of truth, and there is no reason to multiply them here.
    narsnet_rows = load_narsnet_rows()
    matrix = load_comparability()
    for organism in NARSNET_PANELS:
        slug = organism.lower().replace(" ", "_").replace(".", "")
        out = chart_narsnet_organism(
            narsnet_rows, matrix, organism, FIGURES_DIR / "narsnet_{}.png".format(slug)
        )
        if out:
            written.append(out)
        out = chart_comparability(
            matrix, organism, FIGURES_DIR / "narsnet_comparability_{}.png".format(slug)
        )
        if out:
            written.append(out)

    out = chart_surveillance_volume(
        rows, narsnet_rows, FIGURES_DIR / "narsnet_surveillance_volume.png"
    )
    if out:
        written.append(out)

    if args.revisions:
        out = chart_revisions(FIGURES_DIR / "cross_report_revisions.png")
        if out:
            written.append(out)
        else:
            print("  (no cross-report disagreements to chart)")

    for p in written:
        print("  wrote {}".format(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
