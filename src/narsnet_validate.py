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

It pays for itself again, differently, in 2017 and 2018. Those editions print no
numerator and no interval, so none of the checks below reaches them and the
narrative fixtures are the only independent statement about those rows there is.
They are therefore treated differently from the rest: every specimen-stratified
percentage the two chapters state is pinned -- twenty-one of them -- rather than
a representative handful, and each carries the denominator hand-read from the
cell beside it. Four of the twenty-one name no stratum; each is pinned on the
column that prints the figure, and where more than one column does, the note
says which. What none of this amounts to is a per-cell check, and the parser's
module docstring and the extraction report both say so in those words.

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

* `summarise_ci_checks` -- the 2022-2024 counterpart. Those editions print no
  numerator, so the reconciliation check above has nothing to run on; what they
  print instead is a 95% confidence interval, and a percentage sitting outside
  its own interval is a disagreement between two printed figures that needs no
  third one to see. The parser raises the flag; this measures how far outside
  the percentage sits and whether that distance is smaller than half the
  precision the percentage is printed to, which separates a point estimate
  rounded to a whole number from an interval that cannot be read as one at all.

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
    NO_INTERNAL_CHECK_FLAG,
    NUMERATOR_CORRUPT,
    NUMERATOR_NOT_PRINTED,
    is_composite,
    pct_tolerance,
)


def _as_printed(pct) -> str:
    """A percentage back in the form the report printed it in.

    `pct_tolerance` is keyed on printed precision and a record keeps the
    percentage as a float. No cell in any of the twelve tables read so far
    prints a trailing ".0", so a whole-number float was printed as a whole
    number and "%g" recovers it.
    """
    return "%g" % pct


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
    # The 2022-2024 chapters quote the interval as well as the percentage, so a
    # narrative fixture for those editions can corroborate both.
    expected_ci_low: float | None = None
    expected_ci_high: float | None = None
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
    # --- 2017 S. aureus, Ch. narrative (p5) ---------------------------------
    # These two editions print no numerator and no interval, so no check inside
    # a cell reaches them and the fixtures below are the only thing that does.
    # They are weighted accordingly: every percentage the chapters state is
    # pinned, not a sample of them, and the denominator beside each one is
    # hand-read off the table so the two provenances corroborate each other.
    #
    # "S. aureus isolates from blood showed 57.1% resistance to cefoxitin
    #  (surrogate for mecA-mediated oxacillin resistance), overall resistance to
    #  cefoxitin including other sterile body fluids and pus aspirates was found
    #  to be 55.7% (Table 3 and 4)."
    # The 2018 chapter restates the first of these a year later, as 57%.
    NarsNetFixture(SA, "cefoxitin", BLOOD, 2017, 57.1,
                   "narrative (%R; the 2018 chapter restates it as 57%); "
                   "table 4 cell, p6 (denominator)",
                   expected_tested_n=2159),
    NarsNetFixture(SA, "cefoxitin", BLOOD_PA_OSBF, 2017, 55.7,
                   "narrative (%R); table 4 cell, p6 (denominator)",
                   expected_tested_n=3732),
    # "emergence of linezolid resistant S. aureus isolates ... to the extent of
    #  2.2% ... is a matter of concern." The sentence names no stratum, and 2.2
    #  is the figure only the PA+OSBF column prints (1.7 pooled, 1.3 blood).
    NarsNetFixture(SA, "linezolid", PA_OSBF, 2017, 2.2,
                   "narrative (%R, no stratum named; 2.2 is printed by the "
                   "PA+OSBF column alone); table 4 cell, p6 (denominator)",
                   expected_tested_n=1529),
    # "Resistance to gentamicin (aminoglycoside) was observed to be 38.7% for
    #  S. aureus". Again no stratum, and again only one column prints it
    #  (32 pooled, 26.3 blood).
    NarsNetFixture(SA, "gentamicin", PA_OSBF, 2017, 38.7,
                   "narrative (%R, no stratum named; 38.7 is printed by the "
                   "PA+OSBF column alone); table 4 cell, p6 (denominator)",
                   expected_tested_n=1552),
    # Doxycycline is the smallest panel entry and the chapter does not mention
    # it: this one is the table and nothing else.
    NarsNetFixture(SA, "doxycycline", PA_OSBF, 2017, 15.6, "table 4 cell, p6",
                   expected_tested_n=282),

    # --- 2017 E. coli, Ch. narrative (p7) -----------------------------------
    # "E. coli isolated from blood showed 81.4% resistance to cefotaxime and
    #  68.3% to cefepime. Similar trend was observed for urine isolates with
    #  resistance 79.3% to cefotaxime and 72.3% to cefepime."
    NarsNetFixture(EC, "cefotaxime", BLOOD, 2017, 81.4,
                   "narrative (%R); table 5 cell, p7 (denominator)",
                   expected_tested_n=301),
    NarsNetFixture(EC, "cefepime", BLOOD, 2017, 68.3,
                   "narrative (%R); table 5 cell, p7 (denominator)",
                   expected_tested_n=240),
    NarsNetFixture(EC, "cefotaxime", URINE, 2017, 79.3,
                   "narrative (%R); table 5 cell, p7 (denominator)",
                   expected_tested_n=4755),
    NarsNetFixture(EC, "cefepime", URINE, 2017, 72.3,
                   "narrative (%R); table 5 cell, p7 (denominator)",
                   expected_tested_n=1926),
    # "Resistance to carbapenems that is ertapenem and imipenem was observed to
    #  be 36.7% and 25.2% in blood isolates. While in urine isolates, slightly
    #  higher resistance was observed for imipenem (34%) than ertapenem
    #  (30.8%)."
    # The 2018 chapter restates the two blood figures a year later, rounded to
    # 37% and 25%.
    NarsNetFixture(EC, "ertapenem", BLOOD, 2017, 36.7,
                   "narrative (%R; the 2018 chapter restates it as 37%); "
                   "table 5 cell, p7 (denominator)",
                   expected_tested_n=251),
    NarsNetFixture(EC, "imipenem", BLOOD, 2017, 25.2,
                   "narrative (%R; the 2018 chapter restates it as 25%); "
                   "table 5 cell, p7 (denominator)",
                   expected_tested_n=349),
    NarsNetFixture(EC, "imipenem", URINE, 2017, 34.0,
                   "narrative (%R); table 5 cell, p7 (denominator)",
                   expected_tested_n=1260),
    NarsNetFixture(EC, "ertapenem", URINE, 2017, 30.8,
                   "narrative (%R); table 5 cell, p7 (denominator)",
                   expected_tested_n=2233),
    # The first and last rows of the panel, neither named in the chapter, so
    # that the ends of the table are pinned as well as its middle.
    NarsNetFixture(EC, "ampicillin", URINE, 2017, 84.3, "table 5 cell, p7",
                   expected_tested_n=2338),
    NarsNetFixture(EC, "ciprofloxacin", URINE, 2017, 76.1, "table 5 cell, p7",
                   expected_tested_n=3106),

    # --- 2018 S. aureus, Ch. narrative (p6 [5]) -----------------------------
    # "Staph. aureus isolates from blood showed 69% resistance to cefoxitin
    #  (surrogate marker for mecA-mediated oxacillin resistance) which was found
    #  to be higher than that reported in 2017 (57%). Overall resistance to
    #  cefoxitin, including isolates from other sterile body fluids and pus
    #  aspirates, was found to be 63% (Table 4)."
    NarsNetFixture(SA, "cefoxitin", BLOOD, 2018, 69.0,
                   "narrative (%R); table 4 cell, p7 [6] (denominator)",
                   expected_tested_n=3962),
    NarsNetFixture(SA, "cefoxitin", BLOOD_PA_OSBF, 2018, 63.0,
                   "narrative (%R); table 4 cell, p7 [6] (denominator)",
                   expected_tested_n=10607),
    # "Emergence of linezolid resistant Staph. aureus and Enterococcus species
    #  to the extent of 1% and 6% respectively". No stratum, and here it needs
    #  none: all three S. aureus columns print 1.
    NarsNetFixture(SA, "linezolid", BLOOD_PA_OSBF, 2018, 1.0,
                   "narrative (%R, no stratum named; all three columns print "
                   "1); table 4 cell, p7 [6] (denominator)",
                   expected_tested_n=9040),
    # "Resistance to gentamicin was observed to be 19% in Staph. aureus".
    # Two columns print 19 -- the pooled and PA+OSBF -- and the sentence is
    # about the organism rather than a specimen, so it is pinned on the pooled
    # column. The distinction is recorded because it is a real ambiguity in the
    # source, not because it changes the figure.
    NarsNetFixture(SA, "gentamicin", BLOOD_PA_OSBF, 2018, 19.0,
                   "narrative (%R, no stratum named; the pooled and PA+OSBF "
                   "columns both print 19); table 4 cell, p7 [6] (denominator)",
                   expected_tested_n=10119),
    # Vancomycin joins the panel in this edition on fourteen isolates, under a
    # footnote saying so: "% resistance of Staph. aureus against vancomycin is
    # of low statistical validity as the number of isolates tested using broth
    # microdilution method are <=30". Pinned as printed, footnote and all.
    NarsNetFixture(SA, "vancomycin", BLOOD_PA_OSBF, 2018, 0.0,
                   "table 4 cell, p7 [6] (the page footnotes this row as of "
                   "low statistical validity; it is carried as printed)",
                   expected_tested_n=14),

    # --- 2018 E. coli, Ch. narrative (p10 [9]) ------------------------------
    # "E. coli isolated from blood showed 84% resistance to cefotaxime and 63%
    #  to cefepime. E. coli from urine showed higher resistance rates to
    #  cefepime (70%) than those isolated from blood (63%). (Table 6)."
    NarsNetFixture(EC, "cefotaxime", BLOOD, 2018, 84.0,
                   "narrative (%R); table 6 cell, p10 [9] (denominator)",
                   expected_tested_n=500),
    NarsNetFixture(EC, "cefepime", BLOOD, 2018, 63.0,
                   "narrative (%R); table 6 cell, p10 [9] (denominator)",
                   expected_tested_n=496),
    NarsNetFixture(EC, "cefepime", URINE, 2018, 70.0,
                   "narrative (%R); table 6 cell, p10 [9] (denominator)",
                   expected_tested_n=4289),
    # "Resistance to carbapenems that is ertapenem and imipenem was observed to
    #  be 40% and 33% in E.coli blood isolates which is higher than that
    #  observed in 2017 (37% to ertapenem and 25% to imipenem in year 2017)."
    # The second half of that sentence is what corroborates the 2017 fixtures
    # above.
    NarsNetFixture(EC, "ertapenem", BLOOD, 2018, 40.0,
                   "narrative (%R); table 6 cell, p10 [9] (denominator)",
                   expected_tested_n=402),
    NarsNetFixture(EC, "imipenem", BLOOD, 2018, 33.0,
                   "narrative (%R); table 6 cell, p10 [9] (denominator)",
                   expected_tested_n=589),
    # The one drug in either new edition reported for some specimens and not
    # others: nitrofurantoin prints only a pooled and a urine column, with the
    # blood and PA+OSBF blocks greyed out. Pinned so that the greying stays
    # read as greying rather than as a column shifted along.
    NarsNetFixture(EC, "nitrofurantoin", URINE, 2018, 12.0,
                   "table 6 cell, p10 [9] (the blood and PA+OSBF blocks of "
                   "this row are greyed out and emit no record)",
                   expected_tested_n=13194),

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

    # --- 2022 S. aureus, Ch.A narrative (p34 [18]) --------------------------
    # "a significant decrease in the proportion of MRSA in blood was seen from
    #  the year 2018 (69%) to 2021 (59%) and when compared to 2021 the
    #  proportion of MRSA has remained constant in the year 2022 (59%)".
    # The denominator is the Table 5 cell, hand-read off p36; Fig. 7 on the same
    # page prints 5,711 as that year's blood count, which agrees with it.
    NarsNetFixture(SA, "cefoxitin", BLOOD, 2022, 59.0,
                   "narrative (%R); table 5 cell, p36 (denominator)",
                   expected_tested_n=5711),
    # "in the year 2022, none of the S. aureus reported from blood were found to
    #  be resistant to linezolid". The table prints 0 with an interval of 0-0.1.
    NarsNetFixture(SA, "linezolid", BLOOD, 2022, 0.0,
                   "narrative (%R); table 5 cell, p36 (denominator and CI)",
                   expected_tested_n=5827,
                   expected_ci_low=0.0, expected_ci_high=0.1),

    # --- 2022 E. coli, Ch.B narrative (p42 [26]) ----------------------------
    # From this edition on the chapter quotes the interval as well, so these
    # fixtures corroborate both figures from outside the table.
    # "76% (CI:74.1-78) resistance was observed to the drug cefotaxime in blood
    #  isolates"
    NarsNetFixture(EC, "cefotaxime", BLOOD, 2022, 76.0,
                   "narrative (%R and CI); table 7 cell, p44 (denominator)",
                   expected_tested_n=1876,
                   expected_ci_low=74.1, expected_ci_high=78.0),
    # "In urinary isolates ... 74% (CI: 72.9-74.1) resistance was observed to
    #  ciprofloxacin, 58% (CI:57.3- 58.6) to Trimethoprim-Sulfamethoxazole
    #  (TMP/SMX) and 9% (CI:8.9- 9.6) to nitrofurantoin"
    NarsNetFixture(EC, "ciprofloxacin", URINE, 2022, 74.0,
                   "narrative (%R and CI); table 7 cell, p44 (denominator)",
                   expected_tested_n=23227,
                   expected_ci_low=72.9, expected_ci_high=74.1),
    NarsNetFixture(EC, "cotrimoxazole", URINE, 2022, 58.0,
                   "narrative (%R and CI); table 7 cell, p44 (denominator)",
                   expected_tested_n=23163,
                   expected_ci_low=57.3, expected_ci_high=58.6),
    NarsNetFixture(EC, "nitrofurantoin", URINE, 2022, 9.0,
                   "narrative (%R and CI); table 7 cell, p44 (denominator)",
                   expected_tested_n=24953,
                   expected_ci_low=8.9, expected_ci_high=9.6),
    # The cell whose interval is printed with its upper bound below its lower.
    # The chapter does not mention it, so this one is the table and nothing
    # else; it is pinned exactly as printed.
    NarsNetFixture(EC, "doxycycline", OSBF, 2022, 32.0, "table 7 cell, p44",
                   expected_tested_n=139,
                   expected_ci_low=24.2, expected_ci_high=4.02),

    # --- 2023 S. aureus, Ch.1.2.3.1 narrative (p28 [18], p29 [19]) ----------
    # "Approximately half of Staphylococcus aureus isolated from blood (55%;
    #  95% (confidence interval) CI: 53.7-56.6) and from pus aspirates (54%;
    #  95% CI: 53-55) were resistant to cefoxitin"
    NarsNetFixture(SA, "cefoxitin", BLOOD, 2023, 55.0,
                   "narrative (%R and CI); table 6 cell, p30 (denominator)",
                   expected_tested_n=4538,
                   expected_ci_low=53.7, expected_ci_high=56.6),
    NarsNetFixture(SA, "cefoxitin", PUS_ASPIRATE, 2023, 54.0,
                   "narrative (%R and CI, quoted as 53-55); table 6 cell, p30 "
                   "(denominator)",
                   expected_tested_n=10146,
                   expected_ci_low=53.0, expected_ci_high=55.0),
    # The row whose point estimate falls outside its own interval. The chapter
    # states the year's linezolid blood resistance as 0.2% -- "there seems to be
    # a 0.2% rise in resistance to linezolid in this reporting period" -- which
    # is inside the printed interval and rounds to the printed 0. The percentage
    # column is printed to whole numbers and the interval to one decimal.
    NarsNetFixture(SA, "linezolid", BLOOD, 2023, 0.0,
                   "table 6 cell, p30 (the narrative on p29 gives the year's "
                   "figure as 0.2%, which the printed CI brackets and which "
                   "rounds to the printed 0)",
                   expected_tested_n=4896,
                   expected_ci_low=0.1, expected_ci_high=0.4),

    # --- 2023 E. coli, Ch.1.2.3.2 narrative (p36 [26]) ----------------------
    # "A high proportion of resistance to ciprofloxacin was observed with 72%
    #  (CI: 70-73.6) resistance in blood isolates"
    NarsNetFixture(EC, "ciprofloxacin", BLOOD, 2023, 72.0,
                   "narrative (%R and CI); table 8 cell, p38 (denominator)",
                   expected_tested_n=2427,
                   expected_ci_low=70.0, expected_ci_high=73.6),
    # "Fifty-seven percentage of resistance (CI: 54.6- 58.8) to trimethoprim-
    #  sulfamethoxazole was seen among blood isolates"
    NarsNetFixture(EC, "cotrimoxazole", BLOOD, 2023, 57.0,
                   "narrative (%R and CI); table 8 cell, p38 (denominator)",
                   expected_tested_n=2176,
                   expected_ci_low=54.6, expected_ci_high=58.8),
    # "82% (CI: 80.3- 83.7) resistance to cefotaxime was observed in blood
    #  isolates and 75% (CI: 74.9 - 76) in urine isolates"
    NarsNetFixture(EC, "cefotaxime", URINE, 2023, 75.0,
                   "narrative (%R and CI); table 8 cell, p38 (denominator)",
                   expected_tested_n=27068,
                   expected_ci_low=74.9, expected_ci_high=76.0),
    # "Resistance to nitrofurantoin in the urine isolates has increased from 9%
    #  during 2022 to 16% (CI: 15.9 - 16.7) in the current reporting period."
    # The same sentence restates the 2022 figure, which the 2022 fixture above
    # takes from that edition's own chapter.
    NarsNetFixture(EC, "nitrofurantoin", URINE, 2023, 16.0,
                   "narrative (%R and CI); table 8 cell, p38 (denominator)",
                   expected_tested_n=30769,
                   expected_ci_low=15.9, expected_ci_high=16.7),

    # --- 2024 S. aureus, Ch.1.2.3.1 narrative (p24 [17]) -------------------
    # "Approximately half of S. aureus isolated from blood (56%; 95% CI
    #  (confidence interval): 54.7-57.3) were resistant to cefoxitin ...
    #  meanwhile, the resistance to cefoxitin in pus aspirates (54%; 95% CI:
    #  53.2-54.9) and other sterile body fluids (49%; CI: 45.5-51.9)"
    # All three strata, each with its interval, named in one sentence.
    NarsNetFixture(SA, "cefoxitin", BLOOD, 2024, 56.0,
                   "narrative (%R and CI); table 6 cell, p25 (denominator)",
                   expected_tested_n=5967,
                   expected_ci_low=54.7, expected_ci_high=57.3),
    NarsNetFixture(SA, "cefoxitin", PUS_ASPIRATE, 2024, 54.0,
                   "narrative (%R and CI); table 6 cell, p25 (denominator)",
                   expected_tested_n=13694,
                   expected_ci_low=53.2, expected_ci_high=54.9),
    NarsNetFixture(SA, "cefoxitin", OSBF, 2024, 49.0,
                   "narrative (%R and CI); table 6 cell, p25 (denominator)",
                   expected_tested_n=962,
                   expected_ci_low=45.5, expected_ci_high=51.9),

    # --- 2024 E. coli, Ch.1.2.3.2 narrative (p32 [25]) ---------------------
    # "amoxicillin-clavulanate also had high resistance of 68% in blood
    #  isolates. Among carbapenems, ertapenem (49%) had higher resistance rate
    #  than imipenem (40%) and meropenem (36%) in E. coli blood isolates"
    # Percentages only in this chapter; the intervals are the table's.
    NarsNetFixture(EC, "amoxicillin-clavulanate", BLOOD, 2024, 68.0,
                   "narrative (%R); table 8 cell, p34 (denominator and CI)",
                   expected_tested_n=2759),
    NarsNetFixture(EC, "ertapenem", BLOOD, 2024, 49.0,
                   "narrative (%R); table 8 cell, p34 (denominator and CI)",
                   expected_tested_n=1634),
    # "Resistance to nitrofurantoin in urinary isolates showed an increasing
    #  trend over last 3 years (increased from 9% in 2022 to 19% in 2024)."
    NarsNetFixture(EC, "nitrofurantoin", URINE, 2024, 19.0,
                   "narrative (%R); table 8 cell, p34 (denominator and CI)",
                   expected_tested_n=41460),
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
        if fx.expected_ci_low is not None and (
            rec.ci_low is None
            or abs(rec.ci_low - fx.expected_ci_low) > fx.tolerance
        ):
            failures.append(
                "{}: expected CI low {} ({}), got {}".format(
                    fx.label, fx.expected_ci_low, fx.note, rec.ci_low
                )
            )
            continue
        if fx.expected_ci_high is not None and (
            rec.ci_high is None
            or abs(rec.ci_high - fx.expected_ci_high) > fx.tolerance
        ):
            failures.append(
                "{}: expected CI high {} ({}), got {}".format(
                    fx.label, fx.expected_ci_high, fx.note, rec.ci_high
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
            if abs(r.reported_pct - computed) <= pct_tolerance(
                _as_printed(r.reported_pct)
            ):
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


def summarise_unchecked_cells(records):
    """Cells carrying `no_internal_check_possible`, counted by why.

    Descriptive, like the summaries above: the parser has already raised the
    flag. What this adds is the shape of the set, because it is not one
    edition's and the three reasons are different facts about the source. A
    reader who knows only that 2017 and 2018 support no check would otherwise
    take the flag's absence elsewhere to mean a check ran, and on seventeen rows
    in 2020 and 2021 it did not.
    """
    reasons = {
        "no numerator and no interval printed": lambda r: (
            r.numerator_status == NUMERATOR_NOT_PRINTED and r.resistant_pct is not None
        ),
        "numerator corrupt in source, no interval printed": lambda r: (
            r.numerator_status == NUMERATOR_CORRUPT
        ),
        "no percentage printed, so nothing for the counts to disagree with": (
            lambda r: r.resistant_pct is None
        ),
    }
    covered = [
        r for r in records if any(f == NO_INTERNAL_CHECK_FLAG for f in r.flags)
    ]
    by_edition: dict = {}
    for r in covered:
        entry = by_edition.setdefault(r.source_report_year, {"cells": 0, "reasons": {}})
        entry["cells"] += 1
        for label, test in reasons.items():
            if test(r):
                entry["reasons"][label] = entry["reasons"].get(label, 0) + 1
                break
    return {
        "count": len(covered),
        "by_edition": {
            str(year): by_edition[year] for year in sorted(by_edition)
        },
        "rows": [
            {
                "organism": r.organism,
                "antibiotic": r.antibiotic,
                "specimen": r.specimen,
                "source_report_year": r.source_report_year,
                "tested_n": r.tested_n,
                "resistant_n": r.resistant_n,
                "reported_pct": r.reported_pct,
                "numerator_status": r.numerator_status,
                "reconcilable": r.reconcilable,
            }
            for r in sorted(
                covered,
                key=lambda r: (
                    r.source_report_year, r.organism, r.antibiotic, r.specimen
                ),
            )
            # The 2017 and 2018 rows are every row of those editions, so listing
            # them here would restate the dataset. The rows worth naming are the
            # ones a reader would not predict from the edition alone.
            if r.source_report_year not in (2017, 2018)
        ],
    }


CI_EXCLUDES_FLAG = "ci_excludes_point_estimate"
CI_INVERTED_FLAG = "ci_bounds_inverted"


def summarise_ci_checks(records):
    """Rows whose printed percentage sits outside its own printed 95% CI.

    Descriptive, like the summaries above: the parser has already flagged these.
    What this adds is the distance from the percentage to the nearer printed
    bound, and whether that distance is within half the precision the percentage
    is printed to.

    That distinction matters and is the whole reason the distance is reported
    rather than just the count. Where the two figures are printed to different
    precisions -- a percentage to whole numbers beside an interval to one
    decimal -- a value of about 0.2 is printed as 0 and falls a tenth outside an
    interval that in fact contains it. That is a difference in how two columns
    are rounded. An interval whose upper bound is printed below its lower bound
    is not.
    """
    out = []
    for r in sorted(
        (
            r
            for r in records
            if any(f.startswith(CI_EXCLUDES_FLAG) for f in r.flags)
        ),
        key=lambda r: (r.source_report_year, r.organism, r.antibiotic, r.specimen),
    ):
        printed = _as_printed(r.resistant_pct)
        gap = min(
            abs(r.resistant_pct - r.ci_low), abs(r.resistant_pct - r.ci_high)
        )
        out.append(
            {
                "source_report_year": r.source_report_year,
                "organism": r.organism,
                "antibiotic": r.antibiotic,
                "specimen": r.specimen,
                "tested_n": r.tested_n,
                "reported_pct": r.resistant_pct,
                "ci_low": r.ci_low,
                "ci_high": r.ci_high,
                "distance_to_nearer_bound": round(gap, 3),
                "within_the_printed_precision": gap <= pct_tolerance(printed),
                "bounds_inverted": any(
                    f.startswith(CI_INVERTED_FLAG) for f in r.flags
                ),
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
            # None, not zero, where no part printed a numerator. A sum of
            # nothing rendered as 0 would put a count in the report that the
            # page never printed -- next to a composite_resistant_n of null,
            # which reads as a pooled column disagreeing with its parts by its
            # whole size rather than as neither figure existing.
            #
            # Only 2017 and 2018 reach this: they are the only editions that
            # both print a pooled column and print no numerator. No edition from
            # 2021 on prints a pooled column at all, so the 2022-2024 rows, which
            # also print no numerator, never get here.
            printed = [p.resistant_n for p in parts if p.resistant_n is not None]
            resistant_sum = sum(printed) if printed else None
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
                        if comp.resistant_n is None or resistant_sum is None
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
