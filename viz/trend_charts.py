"""Trend charts for the README (spec section 6).

One chart per organism: susceptibility % by year, one line per antibiotic.
Every figure carries the attribution line required by spec section 7.

By default each (organism, antibiotic, year) point is taken from the most
recent report edition that reports it, since later editions supersede earlier
ones. `--revisions` additionally draws a chart showing where editions disagree.

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
from matplotlib.ticker import FuncFormatter, MaxNLocator  # noqa: E402

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
            "Points with fewer than {} isolates tested, points where ICMR "
            "suppressed the percentage, and colistin in the non-fermenter "
            "tables (reported as intermediate susceptibility) are not "
            "plotted.".format(MIN_TESTED_FOR_CHART)
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
        "{} isolates tested, points where ICMR suppressed the percentage, and "
        "colistin in the non-fermenter tables (reported as intermediate "
        "susceptibility, not susceptibility).".format(MIN_TESTED_FOR_CHART),
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
