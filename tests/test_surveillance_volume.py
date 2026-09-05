"""The denominator arithmetic behind the surveillance-volume figure.

Everything else in `viz/` draws numbers that are printed in a source table.
This figure does not: NARS-Net prints a column per specimen, the columns
overlap, and the edition that prints a pooled column is not the same edition
that prints pus aspirate and OSBF separately. So the all-specimen line is
*combined* from what each edition prints, and `_best_disjoint_total` decides
how. Getting that wrong would double-count a stratum or silently understate a
year, and it would look entirely plausible on the chart either way -- which is
why it is pinned here rather than left to the eye.

The figure's caption quotes several of these numbers, so the pins are also what
stops the caption and the line drifting apart.
"""

from __future__ import annotations

from viz.trend_charts import (
    _best_disjoint_total,
    amrsn_volume,
    load_narsnet_rows,
    load_rows,
    narsnet_volume,
)

EC = "Escherichia coli"
SA = "Staphylococcus aureus"


# ---------------------------------------------------------------------------
# The combining rule, on its own
# ---------------------------------------------------------------------------


def test_pooled_column_is_preferred_over_a_partial_sum():
    """2017 E. coli prints blood, urine and a four-way pooled column. Summing
    blood and urine would miss pus aspirate and OSBF, which that edition prints
    nowhere else; the pooled column covers all four and is used as printed."""
    printed = {"blood": 222, "urine": 2338, "blood+urine+pus_aspirate+osbf": 3011}
    assert _best_disjoint_total(printed) == 3011


def test_disjoint_strata_are_summed_when_no_pooled_column_exists():
    """2021 onward: four columns, no pooled column anywhere in the edition."""
    printed = {"blood": 2748, "osbf": 1920, "pus_aspirate": 10466, "urine": 37565}
    assert _best_disjoint_total(printed) == 52699


def test_a_stratum_is_never_counted_twice():
    """The pooled column and its own constituents cannot both be taken."""
    printed = {"blood": 100, "urine": 200, "blood+urine": 300}
    assert _best_disjoint_total(printed) == 300


def test_wider_coverage_wins_over_a_larger_number():
    """Coverage, not size, decides: a bigger column covering fewer strata is
    the wrong answer, because the figure is counting isolates across all
    specimens rather than finding the largest printed figure."""
    printed = {"urine": 9000, "blood": 10, "pus_aspirate": 10, "osbf": 10}
    assert _best_disjoint_total({"urine": 9000}) == 9000
    assert _best_disjoint_total(printed) == 9030


def test_fewest_columns_breaks_a_tie_on_coverage():
    """Where a pooled column and its partition cover the same strata, the
    printed pooled figure is used rather than a sum this project computed."""
    printed = {"blood": 100, "urine": 200, "blood+urine": 305}
    assert _best_disjoint_total(printed) == 305


def test_a_drug_printed_in_one_column_only():
    """2019 E. coli nitrofurantoin: reported for urine, other blocks greyed."""
    printed = {"urine": 16741, "blood+urine+pus_aspirate+osbf": 16741}
    assert _best_disjoint_total(printed) == 16741


def test_no_columns_yields_nothing_rather_than_zero():
    assert _best_disjoint_total({}) is None


def test_the_optimum_is_unique_for_every_drug_year_in_the_data():
    """The rule ranks on (strata covered, fewest columns) and nothing else, so
    two subsets tying on both would fall through to iteration order -- which is
    deterministic, columns being sorted, but arbitrary. It never fires: across
    all 172 drug-years no two optimal subsets exist at all, let alone two
    giving different totals. Pinned because the figure's caption quotes these
    numbers, and a value settled by iteration order would not be a fact about
    the source.
    """
    rows = load_narsnet_rows()
    printed_by_key: dict = {}
    for row in rows:
        key = (row["organism"], row["antibiotic"], row["year"])
        printed_by_key.setdefault(key, {})[row["specimen"]] = int(row["tested_n"])
    assert len(printed_by_key) == 172

    for key, printed in printed_by_key.items():
        columns = sorted(printed)
        optima: list = []
        for mask in range(1, 1 << len(columns)):
            chosen = [columns[i] for i in range(len(columns)) if mask >> i & 1]
            covered: set = set()
            for specimen in chosen:
                parts = frozenset(specimen.split("+"))
                if parts & covered:
                    break
                covered |= parts
            else:
                optima.append(
                    ((len(covered), -len(chosen)), sum(printed[s] for s in chosen))
                )
        best = max(rank for rank, _total in optima)
        winners = {total for rank, total in optima if rank == best}
        assert len(winners) == 1, "{}: {} optimal subsets".format(key, len(winners))
        assert winners.pop() == _best_disjoint_total(printed)


# ---------------------------------------------------------------------------
# The three plotted series, against the real datasets
# ---------------------------------------------------------------------------


def test_narsnet_blood_series_is_the_largest_blood_denominator():
    rows = load_narsnet_rows()
    blood = narsnet_volume(rows, EC, specimen="blood")
    assert sorted(blood) == list(range(2017, 2025))
    assert blood[2017] == 453
    assert blood[2024] == 3254


def test_where_the_narsnet_volume_series_falls():
    """The NARS-Net series is not monotone, and the exceptions are not the same
    for the two organisms, so they are pinned rather than generalised.

    2020 falls on every series: the 2020 edition was published from inside the
    pandemic and says plainly why its isolate counts are down. S. aureus falls
    again in 2023 -- steeply on blood (5,947 to 5,074) and by 84 isolates on
    the all-specimen line -- where E. coli keeps rising. Nothing in the reports
    ties that to the unrelated AMRSN dip in the same year, and this test does
    not imply one.
    """
    rows = load_narsnet_rows()

    def falls(series):
        return [y + 1 for y in range(2017, 2024) if series[y + 1] < series[y]]

    assert falls(narsnet_volume(rows, EC, specimen="blood")) == [2020]
    assert falls(narsnet_volume(rows, EC)) == [2020]
    assert falls(narsnet_volume(rows, SA, specimen="blood")) == [2020, 2023]
    assert falls(narsnet_volume(rows, SA)) == [2020, 2023]


def test_narsnet_all_specimen_series_exceeds_its_own_blood_series():
    rows = load_narsnet_rows()
    for organism in (EC, SA):
        blood = narsnet_volume(rows, organism, specimen="blood")
        every = narsnet_volume(rows, organism)
        for year in blood:
            assert every[year] >= blood[year]


def test_amrsn_volume_uses_the_latest_edition_to_report_each_year():
    """Same rule as `latest_edition_series`, so the volume figure and the AMRSN
    trend charts cannot quote different denominators for one year. E. coli
    piperacillin-tazobactam 2022 is the case that separates them: 14,729 in the
    2022 and 2023 editions, 14,728 in the 2024 edition."""
    rows = load_rows()
    assert amrsn_volume(rows, EC)[2022] == 14728


def test_the_2023_amrsn_dip_is_present_in_the_series():
    """Quoted in the figure's caption, so pinned here. It is in the source: the
    2023 and 2024 editions print the 2023 figures identically."""
    volume = amrsn_volume(load_rows(), EC)
    assert volume[2023] < volume[2022]
    assert volume[2023] < volume[2024]
    assert (volume[2022], volume[2023], volume[2024]) == (14728, 7611, 12445)


def test_narsnet_overtakes_amrsn_on_e_coli_but_not_on_s_aureus():
    """The shape the figure exists to show, stated as an assertion so that a
    change in the combining rule cannot quietly reverse it."""
    narsnet_rows, amrsn_rows = load_narsnet_rows(), load_rows()
    ec_every = narsnet_volume(narsnet_rows, EC)
    ec_amrsn = amrsn_volume(amrsn_rows, EC)
    assert ec_every[2017] < ec_amrsn[2017]
    assert ec_every[2024] > ec_amrsn[2024]

    # S. aureus blood never catches the AMRSN pooled column.
    sa_blood = narsnet_volume(narsnet_rows, SA, specimen="blood")
    sa_amrsn = amrsn_volume(amrsn_rows, SA)
    assert all(sa_blood[y] < sa_amrsn[y] for y in sa_blood)
