# NARS-Net V3 cross-reference — research findings, gap analysis, and investigation prompt

Prepared 1 September 2026 for `icmr-amr-tracker` V3 scoping.
Every factual claim below is sourced to a document that was actually retrieved and read. Where something could
not be determined, it says so rather than filling the gap with a plausible guess.

---

## Corrections to the starting assumptions

Four of the seven starting assumptions held. Three need adjusting:

1. **"Covers nine priority pathogens" — true only from 2023 onward.** NARS-Net covered **seven** pathogens from
   2017 through 2022 (S. aureus, Enterococcus, E. coli, Klebsiella, Pseudomonas, Acinetobacter, Salmonella
   Typhi/Paratyphi). *Shigella* and *Vibrio cholerae* first appear as reported organisms in the **2023** edition.
   Any V3 text describing NARS-Net as a nine-pathogen network must be scoped to 2023+.
2. **"~54–60 sentinel sites"** — both numbers are right but they mean different things and should not be used
   interchangeably: **54 sites submitted data** for calendar 2024, while the **network roster** stands at
   **60 laboratories** as of March 2025. Site count grew monotonically across the series: 13→20→29→30→36→40→50→60
   in the network, with 10→16→21→29→35→36→41→54 actually submitting.
3. **"Feeds into WHO-GLASS"** — true, but with a consequence that matters for V3. NCDC's own SOP states it submits to
   GLASS *"the aggregated AMR surveillance data from the **National and State level** AMR Surveillance Networks"*
   ([SOP, 2nd ed. Jan 2023](https://ncdc.mohfw.gov.in/uploads/pdf/amr9.pdf)). India's GLASS submission is therefore a
   **larger and different population** than the NARS-Net annual report. GLASS-derived Indian figures are not a
   substitute source for NARS-Net report figures, and mixing them would silently change the denominator.

Confirmed as stated: NCDC-run and separate from ICMR; genus-level reporting for Klebsiella/Pseudomonas/Acinetobacter;
E. coli and S. aureus as the comparable pair; WHONET-based validation; reports for 2017–2024 at
[ncdc.mohfw.gov.in/reports/](https://ncdc.mohfw.gov.in/reports/).

---

# PART A — FINDINGS

## A1. Genus vs species reporting level, per pathogen, per edition

**Confirmed, and it holds across all eight editions.** *Klebsiella*, *Pseudomonas* and *Acinetobacter* are reported at
**genus level only** in every edition from 2017 to 2024. Every table, figure and annexure in all eight PDFs was checked.
There is **no species-level breakdown anywhere** — not in a supplementary table, not in an annex, not in a figure.
The strings *aeruginosa* and *baumannii* do not appear as data labels in any edition of the series.

Reporting level by organism, stable across the series:

| Pathogen | Printed label | Level |
|---|---|---|
| *Staphylococcus aureus* | `Staphylococcus aureus` / `Staph. aureus` / `S. aureus` | **species** |
| *Escherichia coli* | `Escherichia coli` / `E. coli` / `Escherichia Coli` (sic, 2020–22) | **species** |
| *Enterococcus* | `Enterococcus species` / `Enterococcus spp.` / `Enterococci species` (2017) | genus |
| *Klebsiella* | `Klebsiella species` / `Klebsiella spp.` | **genus** |
| *Pseudomonas* | `Pseudomonas species` / `Pseudomonas spp.` | **genus** |
| *Acinetobacter* | `Acinetobacter species` / `Acinetobacter spp.` | **genus** |
| *Salmonella* Typhi/Paratyphi | `Salmonella enterica serotype Typhi and Paratyphi` | serovar |
| *Shigella* (2023+) | `Shigella species` | genus |
| *Vibrio cholerae* (2023+) | `Vibrio cholerae` | species |

### The one exception, and why it is not usable data

In the **2017** edition ([amr39.pdf](https://ncdc.mohfw.gov.in/uploads/pdf/amr39.pdf)), the **Table 1 column header
reads `Klebsiella pneumoniae`** — species level. But Table 2 and the results table (Table 6) in the *same document*
both say "Klebsiella species", as does all narrative text. It is a labelling inconsistency in a single header cell,
corrected to "Klebsiella species" in 2018 and never recurring. **Do not treat 2017 as species-resolved Klebsiella data.**

Separately, `K. pneumoniae` appears in the deduplication worked example in the 2019, 2020, 2021, 2022 and 2023
editions ("*if the growth of E. coli is detected in one culture and of K. pneumoniae in the other, both results are
considered*"). That is illustrative prose explaining the dedup rule, not a data label.

### The upstream/published mismatch — worth a sentence in the V3 docs

The governing [NARS-Net laboratory SOP](https://ncdc.mohfw.gov.in/uploads/pdf/amr9.pdf) defines the priority list at a
*narrower* taxonomic level than the annual report publishes — "*Acinetobacter baumannii/Acinetobacter calcoaceticus*
complex" and "*Pseudomonas aeruginosa*" — and carries an extended WHONET species-code table (*K. oxytoca* `kox`,
*K. aerogenes* `eae`, etc.). So species-level identification is specified at collection and species data exists in the
WHONET files; the annual report aggregates to genus for publication. This is a **publication-granularity choice, not a
laboratory limitation**, and framing it that way is both accurate and appropriately neutral.

**Scope consequence for V3:** E. coli and S. aureus are the only genuinely comparable organisms. K. pneumoniae,
P. aeruginosa and A. baumannii cannot be compared without comparing a species against a genus, which would be an
apples-to-oranges construction regardless of how carefully it were caveated.

---

## A2. E. coli and S. aureus antibiotic panels, per edition, with AMRSN overlap

### E. coli panel as printed, by edition

| Year | n | Drugs (printed form) |
|---|---|---|
| 2017 | 7 | Ampicillin · Cefotaxime · **Ceftazidime** · Cefepime · Ertapenem · Imipenem · Ciprofloxacin |
| 2018 | 8 | Ampicillin · Cefotaxime · Cefepime · Ertapenem · Imipenem · Ciprofloxacin · Trimethoprim/Sulfamethoxazole · Nitrofurantoin |
| 2019 | 9 | as 2018 + Colistin; `TMP/SMX` abbreviated again |
| 2020 | 9 | Ampicillin · Cefotaxime · Cefepime · Ertapenem · Imipenem · Ciprofloxacin · TMP/SMX · Nitrofurantoin · Colistin |
| 2021 | 17 | + Amikacin · Amoxicillin/ Clavulanic acid · Gentamicin · Meropenem · Piperacillin/ Tazobactam · Fosfomycin · Cefuroxime · Doxycycline |
| 2022 | 17 | same molecules as 2021; abbreviations change to `Amox-clav`, `TMP/SMX` |
| 2023 | 17 | **Cefuroxime dropped, Ceftriaxone added** — same count, different set. Labels: Ampicillin, Amox/Clav, Pip/Taz, Ceftriaxone, Cefotaxime, Cefepime, Ertapenem, Imipenem, Meropenem, Amikacin, Gentamicin, Ciprofloxacin, TMP/SMX, Colistin, Fosfomycin, Nitrofurantoin, Doxycycline |
| 2024 | 17 | as 2023; labels render as `Amox-Clav`, `Pip-Taz`, `TMP-SMX` |

> **Trap:** 2021, 2022, 2023 and 2024 all have "17 drugs", but 2023 is not the same seventeen as 2022. A naive
> panel-size comparison would miss the cefuroxime→ceftriaxone swap.

### S. aureus panel as printed, by edition

| Year | n | Drugs (printed form) |
|---|---|---|
| 2017 | 9 | Cefoxitin · Erythromycin · Clindamycin · TMP/SMX · **Gentamycin** (sic) · Ciprofloxacin · Linezolid · Doxycycline · Tetracycline |
| 2018 | 10 | as 2017 + **Vancomycin\*** (n=14, footnoted as low statistical validity); spelling corrected to Gentamicin |
| 2019 | 8 | Vancomycin and Tetracycline both removed |
| 2020 | 8 | Cefoxitin · Gentamicin · Ciprofloxacin · TMP/SMX · Clindamycin · Erythromycin · Linezolid · Doxycycline |
| 2021 | 9 | + **Teicoplanin** |
| 2022 | 9 | frozen |
| 2023 | 9 | Cefoxitin · Ciprofloxacin · Clindamycin · Doxycycline · Erythromycin · Gentamicin · Linezolid\* · TMP/SMX · Teicoplanin |
| 2024 | 9 | as 2023 |

**Oxacillin never appears as a row in any edition** — cefoxitin is the sole MRSA surrogate throughout, stated
explicitly in 2022 as "*a surrogate marker for mecA-mediated oxacillin resistance or MRSA*".
**Vancomycin is a printed row only in 2018.** The 2019 and 2020 editions explain the omission ("*none of the sites…
reported MIC results for vancomycin using broth microdilution*"); 2022 reports screening in prose only
(1 confirmed resistant of 11,151 screened, confirmed at the NCDC NRL). This is a **method-availability constraint,
not an omission of interest** — worth saying plainly in the V3 docs, in the project's established register.

### Overlap with the AMRSN panels

**S. aureus — 7 of AMRSN's 11 drugs overlap** (2021–2024 NARS-Net panel):

| Overlapping | AMRSN-only | NARS-Net-only |
|---|---|---|
| cefoxitin, ciprofloxacin, clindamycin, erythromycin, linezolid, teicoplanin, **cotrimoxazole ≡ TMP/SMX** | oxacillin, tetracycline, tigecycline, vancomycin | doxycycline, gentamicin |

For 2019–2020 the overlap drops to **6 of 11** (no teicoplanin). For 2017–2018 it is **6 of 11** plus tetracycline
(=7), and 2018 alone also carries vancomycin (=8) — though at n=14 the 2018 vancomycin row is not analytically usable.

**E. coli — 7 of AMRSN's 10 drugs overlap** (2021–2024 panel), checked against the repo's actual ten-drug
Enterobacterales `CANONICAL_PANEL` (the denominator is 10, not the 8 the brief listed):

| Year | Overlapping AMRSN drugs (of 10) | Count |
|---|---|---|
| 2017 | cefotaxime, **ceftazidime**, ciprofloxacin, ertapenem, imipenem | 5 |
| 2018–2020 | cefotaxime, ciprofloxacin, ertapenem, imipenem | **4** |
| 2021–2024 | amikacin, cefotaxime, ciprofloxacin, ertapenem, imipenem, meropenem, piperacillin-tazobactam | **7** |

The two AMRSN Enterobacterales drugs that are **never** in any NARS-Net E. coli panel are **cefazolin** and
**levofloxacin**; a third, **ceftazidime**, is in a NARS-Net E. coli table in 2017 only.

**Ceftazidime is the standing miss.** It is in the AMRSN panel but appears in a NARS-Net E. coli table **only in 2017**.
Note a source inconsistency worth documenting: in the **2019** edition ceftazidime is absent from Table 6 but *does*
appear in the E. coli bar charts (Figs. 13, 14) — same pattern for Klebsiella (Figs. 15/16 vs Table 7). So a
ceftazidime value exists in 2019 in figure form only, not in the table.

### Naming variants requiring normalisation

| Concept | Forms seen |
|---|---|
| trimethoprim-sulfamethoxazole | `TMP/SMX` (2017, 2019–2023) · `TMP-SMX` (2024 Tables 8/9) · `TMP / SMX` (2021) · `Trimethoprim/Sulfamethoxazole` (2018, 2021) · `Trimethoprim/sulfamethoxazole` (footnotes) — vs repo's `cotrimoxazole` |
| amoxicillin-clavulanate | `Amoxicillin/ Clavulanic acid` (2021) · `Amox-clav` (2022) · `Amox/Clav` (2023 table) · `Amox-clav` (2023 footnote, inconsistent with its own table) · `Amox-Clav` (2024) |
| piperacillin-tazobactam | `Piperacillin/ Tazobactam` (2021) · `Pip/Taz` (2023) · `Pip-Taz` (2024) — vs repo's `piperacillin-tazobactam` |
| gentamicin | `Gentamycin` (2017) · `Gentamicin` (2018+) |

Note also that the **2024 report is internally inconsistent**: `TMP/SMX` in Table 6 (S. aureus) but `TMP-SMX` in
Table 8 (E. coli), in the same document. Normalisation must be per-cell, not per-edition.

---

## A3. Direct URLs, verified

All eight were fetched and returned extractable text. **None are scanned images, none require login, none 404.**
The legacy `/uploads/pdf/amrNN.pdf` path is the one to use — it renders reliably where the `wp-content` copies truncate.

| Data year | URL | Verified |
|---|---|---|
| 2017 | https://ncdc.mohfw.gov.in/uploads/pdf/amr39.pdf | text ✓ |
| 2018 | https://ncdc.mohfw.gov.in/uploads/pdf/amr38.pdf | text ✓ |
| 2019 | https://ncdc.mohfw.gov.in/uploads/pdf/amr37.pdf | text ✓ |
| 2020 | https://ncdc.mohfw.gov.in/uploads/pdf/amr36.pdf | text ✓ |
| 2021 | https://ncdc.mohfw.gov.in/uploads/pdf/amr35.pdf | text ✓ |
| 2022 | https://ncdc.mohfw.gov.in/uploads/pdf/amr34.pdf | text ✓ |
| 2023 | https://ncdc.mohfw.gov.in/uploads/pdf/amr32.pdf | text ✓ |
| 2024 | https://ncdc.mohfw.gov.in/uploads/pdf/amr30.pdf | text ✓ |

`wp-content` equivalents also exist and work, with one caveat — the 2024 one truncates before Annexure I:
2023 = `/wp-content/uploads/2024/09/Final-Annual-Report-2023-06_08_2024.pdf`,
2024 = `/wp-content/uploads/2025/09/Final_Annual-Report-2025_Jan-to-Dec-2024.pdf`.

**Three traps:**
- **Cover-page years lie.** The 2019-data report's cover reads "AMR Annual report **-2020**"; the 2020-data report's
  cover reads "Annual Report**-2021**". Cite by reporting period, never by the cover number.
- `wp-content/uploads/2024/03/87909365291642417515.pdf` is a **duplicate of the 2020 edition**, not a distinct year.
  It is the URL cited by several published papers, which compounds the year confusion.
- The NCDC `/reports/` index **strips `href`s from every fetcher**, and the WordPress REST API is disabled. The way
  these URLs were recovered was the Wayback CDX index:
  `https://web.archive.org/cdx/search/cdx?url=ncdc.mohfw.gov.in&matchType=domain&fl=original&collapse=urlkey&filter=original:.*/uploads/pdf/amr.*`
  Worth recording in the repo's method notes, since it is the only reproducible route.

---

## A4. Table locations, and counts vs percentages

### Table numbers per edition

| Year | E. coli | S. aureus | Caption form |
|---|---|---|---|
| 2017 | Table 5 | Table 4 | "Resistance (%) in *X*" |
| 2018 | Table 6 | Table 4 | "Resistance (%) in *X* observed in year 2018" |
| 2019 | Table 6 | Table 4 | "Resistance profile of *X*" |
| 2020 | Table 8 | Table 5 | "Specimen wise resistance profile of *X*" |
| 2021 | Table 6 | Table 4 | "Resistance profile of *X*" |
| 2022 | Table 7 | Table 5 | "Resistance profile of *X* (N=…)" |
| 2023 | Table 8 | Table 6 | "Resistance profile of *X* (N=…)" |
| 2024 | Table 8 | Table 6 | "Resistance profile of *X* (N=…)" |

Table numbers are **not stable across editions** — the extractor must locate tables by caption match, not index.
Note also that List-of-Tables captions and in-body captions differ in several editions (2019, 2020, 2024), so
caption matching needs to be fuzzy.

### The critical finding: numerator availability changes twice mid-series

| Years | Printed columns | Numerator | 95% CI |
|---|---|---|---|
| 2017, 2018 | `No. tested` · `% Resistance` | **No** | No |
| **2019, 2020** | `Number tested` · **`Number Resistant`** · `%R` | **Yes** | No |
| **2021** | `Number Tested` · `Number Resistant` · `(%) Resistance` | **Partial** (see below) | No |
| 2022, 2023, 2024 | `Number Tested` · `(%R)` · `95% CI` | **No** | Yes |

**Every edition prints the denominator. 2019 and 2020 print a usable numerator throughout; 2021 prints one that is
only partly usable; 2022–2024 print none.**

This is the single most consequential fact for V3, because the repo's reconciliation-checking approach — comparing a
printed percentage against its own printed counts — is **fully possible only for 2019 and 2020**. For **2021** it
holds for the S. aureus table and for the Pus Aspirate and OSBF columns of the E. coli table, but **not for the
E. coli Blood column or two E. coli Urine cells**, where the printed `Number Resistant` values are corrupt in the
source (rows where `Number Resistant` exceeds `Number Tested`, and rows whose `Number Resistant` implies a
percentage far from both the printed percentage and the corroborating figure — confirmed by rendering the page).
The printed `%R` column and `Number Tested` are sound throughout 2021. For 2017–2018 and 2022–2024 an approximate
numerator can be back-computed as denominator × %R, but %R is rounded to whole integers on most rows, so the
recovered numerator carries roughly ±0.5% of the denominator in error. That is a derived quantity and should be
labelled as such, in the same way `computed_pct` already is.

### Correction: running the check on 2019 and 2020 — 8 cells of 108 do not reconcile

The statement above that the check is *possible* throughout 2019 and 2020 holds: every cell in those four tables
prints a numerator, a denominator and a percentage. Running it is a separate matter, and the paragraph above is too
strong in implying that the cells therefore agree. They do not, in eight places.

This was established during V3 extraction by reading all 108 printed cells by eye off the rendered pages —
`narsnet_2019.pdf` p24 (Table 4, S. aureus) and p29 (Table 6, E. coli), `narsnet_2020.pdf` p25 (Table 5, S. aureus)
and p33 (Table 8, E. coli) — independently of this document, so that a transcription slip here could not propagate
into the finding. A cell is counted as reconciling when the printed percentage is within half of its own printed
precision of numerator over denominator: 0.5 for a percentage printed as a whole number, 0.05 for one printed to one
decimal. **All eight cells below are carried in the dataset exactly as printed, and flagged. Neither the numerator nor
the percentage is corrected.**

**Seven marginal cases, all in the same direction.** Each computes to between .46 and .49 above a whole number and is
printed as the next integer up:

| Edition | Organism | Drug | Specimen | Printed counts | Computed | Printed %R |
|---|---|---|---|---|---|---|
| 2019 | S. aureus | Gentamicin | Blood | 1,163 / 4,390 | 26.49 | 27 |
| 2020 | S. aureus | Cefoxitin | PA+OSBF | 2,357 / 4,580 | 51.46 | 52 |
| 2020 | S. aureus | Ciprofloxacin | Blood+PA+OSBF | 4,798 / 7,110 | 67.48 | 68 |
| 2020 | S. aureus | Ciprofloxacin | PA+OSBF | 2,922 / 4,087 | 71.49 | 72 |
| 2020 | E. coli | Ampicillin | PA+OSBF | 2,291 / 2,590 | 88.46 | 89 |
| 2020 | E. coli | Cefotaxime | Urine | 6,169 / 8,068 | 76.46 | 77 |
| 2020 | E. coli | Imipenem | Blood | 330 / 1,049 | 31.46 | 32 |

The consistency of the pattern — seven cells, all rounding up from .46–.49, none rounding down — is more consistent
with the percentage having been computed from a slightly different set of isolates than the counts printed beside it
than with either figure being wrong. The discrepancy is at most 0.54 percentage points in every case.

**One case of a different kind.** In the 2020 edition, Table 5, *S. aureus*, doxycycline, Blood column: the printed
counts are **24 resistant of 2,638 tested**, which is 0.91%, printed beside a **%R of 12**. This is not a rounding
difference. For context, the same row prints 725 resistant in the Blood+PA+OSBF column and 402 in PA+OSBF, and
725 − 402 = 323, which against 2,638 is 12.2% — so the Blood numerator behaves like a printing defect of the same
family as the 2021 E. coli Blood column recorded in B5, rather than like a disagreement between two calculations.
The printed `%R` and `Number Tested` are consistent with the rest of the table.

**A cross-column disagreement in 2019, not covered by the within-cell check.** In the 2019 edition, Table 6,
*E. coli*, nitrofurantoin is reported for urine only; the Blood and PA+OSBF blocks are greyed out. The pooled
Blood+Urine+PA+OSBF column and the Urine column both print a denominator of **16,741**, which for a urine-only drug
must be the same isolates, but the pooled column prints **2,026** resistant against the Urine column's **2,042**.
Both round to 12%. Because this is a disagreement between two columns rather than inside one cell, the repository's
per-cell reconciliation check does not see it; it needs a cross-column check at validator level.

**Consequence for the V3 reconciliation window.** "2019 and 2020 reconcile fully" should be read as "the check can be
run on every cell in 2019 and 2020", not as "every cell agrees". 100 of the 108 cells agree within their printed
precision.

These tables also report every drug separately by specimen type instead of pooling — more work to produce, and the
only reason a specimen-matched comparison between the two networks is possible at all.

### Extending the check to 2021 — what the two tables show, cell by cell

B5 below records the 2021 *E. coli* Blood column as corrupt at source. That entry was written from a rendering of
the page during the investigation. When the parser was extended to the edition, all **84** printed cells of the two
2021 tables were read by eye off `narsnet_2021.pdf` p24 (Table 4, *S. aureus*) and p29 (Table 6, *E. coli*),
independently of this document, so that what follows is a second reading rather than a copy of the first.

The counts, by column:

| Table | Column | Cells | Reconcile |
|---|---|---|---|
| Table 4, *S. aureus* | Blood, Pus aspirate, OSBF | 27 | **27** |
| Table 6, *E. coli* | Pus Aspirate | 14 | **14** |
| Table 6, *E. coli* | OSBF | 14 | **14** |
| Table 6, *E. coli* | Urine | 16 | **14** (Pip/Taz and TMP/SMX do not) |
| Table 6, *E. coli* | Blood | 13 | **2** (Amox-clav and Colistin do) |

**One refinement to B5.** The Blood `Number Resistant` sub-column does not reconcile in **11 of its 13 cells**, not
in all thirteen. Amoxicillin/clavulanic acid prints 390 of 680 beside a printed 57, and colistin prints 0 of 914
beside a printed 0; both agree.

**The Blood figures are the column's own values, printed against the wrong rows.** Taking each Blood row's printed
denominator and printed percentage and asking which of the thirteen printed numerators would satisfy it gives
exactly one candidate per row, and the answer is a one-to-one matching:

| Row (`N`, printed %R) | Numerator that satisfies it | Row it is actually printed against |
|---|---|---|
| Amikacin (1,510, 29) | 431 | Gentamicin |
| Ampicillin (1,294, 84) | 1,088 | Amikacin |
| Cefepime (1,286, 62) | 797 | Cefotaxime |
| Cefotaxime (1,380, 77) | 1,056 | Cefepime |
| Ciprofloxacin (1,551, 63) | 981 | Meropenem |
| Ertapenem (406, 33) | 135 | Ciprofloxacin |
| Gentamicin (1,260, 39) | 491 | Imipenem |
| Meropenem (854, 25) | 211 | Ertapenem |
| Piperacillin/Tazobactam (1,350, 43) | 584 | Ampicillin |
| Trimethoprim/Sulfamethoxazole (1,289, 54) | 701 | Piperacillin/Tazobactam |
| Amoxicillin/Clavulanic acid (680, 57) | 390 | Amoxicillin/Clavulanic acid |
| Colistin (914, 0) | 0 | Colistin |
| Imipenem (1,593, 29) | — none of the thirteen | — |

Twelve of the thirteen printed values are the right values in the wrong places; `14`, printed against
Trimethoprim/Sulfamethoxazole, matches no row, and imipenem's own numerator (which would be about 462) does not
appear in the column at all. The two cells that reconcile are the two the displacement happens to have left in
place. **None of this is used to repair anything** — the printed figures are carried exactly as printed. It is
recorded because it says what kind of defect this is: not thirteen wrong numbers, but one sub-column that did not
survive being set.

**What the extractor does with it.** `CORRUPT_NUMERATORS` in `src/parsers/narsnet_parser.py` declares the whole
Blood sub-column and the two named Urine cells — 15 cells. Those rows carry `numerator_status =
corrupt_in_source`, `reconcilable = false` and no `computed_pct`; `resistant_n` still holds what the page prints.
The two agreeing Blood cells are declared along with the rest, because which values in a displaced column came to
rest on their own row is not something the printed table lets a reader establish; the extraction report counts them
so the decision is visible rather than buried. Declaring the cells by hand, rather than by a rule on the size of the
disagreement, is what keeps this apart from the eight 2019–2020 `pct_mismatch` cells above — including the 2020
doxycycline Blood cell, which such a rule would have swept in.

**The percentages are recoverable because the chapter states them.** The 2021 *E. coli* chapter (p19) gives the
Blood figures for ciprofloxacin (63), TMP/SMX (54) and piperacillin-tazobactam (43), and carbapenem resistance in
blood "up to 33%", in prose written independently of the table. Those are four of the thirteen cells whose
numerator is unusable, and the prose confirms the printed `%R` for each. The 2021 *S. aureus* chapter does the same
for methicillin (59 / 49 / 48) and erythromycin (63 / 51 / 54), naming the stratum in each case.

### Extending the check to 2022, 2023 and 2024 — a different check, because the columns changed

These three editions print `Number Tested`, a percentage and a **95% confidence interval**, and no numerator at
all. The reconciliation check above therefore has nothing to run on: with no numerator there is no second figure
inside the cell for the percentage to disagree with. A numerator is **not** back-computed as denominator × %R —
that would be the only invented count in the repository, and checking the percentage against it would be circular.
Every one of the 258 rows from these editions carries `numerator_status = not_printed_in_source`,
`reconcilable = false` and no `resistant_n`.

What these editions do support is a check the earlier ones cannot: **the printed percentage against its own printed
interval.** A percentage and a confidence interval are two printed statements about one quantity, so they can
disagree without any third figure being available. All 258 cells were read by eye off `narsnet_2022.pdf` p36 and
p44, `narsnet_2023.pdf` p30 and p38, and `narsnet_2024.pdf` p25 and p34, independently of this document.

**Two cells of 258 sit outside their own interval, and they are not the same kind of thing.**

| Edition | Organism | Drug | Specimen | `N` | Printed %R | Printed 95% CI | Distance to the nearer bound |
|---|---|---|---|---|---|---|---|
| 2023 | *S. aureus* | Linezolid | Blood | 4,896 | 0 | 0.1–0.4 | 0.1 |
| 2022 | *E. coli* | Doxycycline | OSBF | 139 | 32 | 24.2–4.02 | 7.8 |

**The linezolid row is a difference between how two columns are rounded.** B5 below records it as internally
inconsistent. Reading the page, and the chapter beside it, makes a narrower statement available. The percentage
column is printed to whole numbers and the interval to one decimal, and the 2023 chapter (p19) states the year's
linezolid figure as **0.2%** — "there seems to be a 0.2% rise in resistance to linezolid in this reporting period".
A value of 0.2 sits inside the printed interval and rounds to the printed 0. The interval, the narrative and the
point estimate are all consistent with one another once the printed precision of each column is taken into account;
what the check has caught is the rounding, not a disagreement about the underlying figure.

**The doxycycline row is not.** Its interval is printed `24.2- 4.02`: the upper bound is below the lower one, so
the interval as printed is empty and the point estimate of 32 is outside it by any reading. The bounds are carried
in the order they are printed and are **not** swapped, because swapping them would be a repair. No reconstruction
of the intended upper bound is offered here; the printed figures are what the dataset carries.

The distinction is reported rather than left implicit: `summarise_ci_checks` records the distance to the nearer
bound and whether that distance is within half the precision the percentage is printed to, so the size of each
finding can be judged rather than assumed. It is the same posture `summarise_composite_sums` takes.

### Panel membership, not panel size — the 2023 swap

2022, 2023 and 2024 each print a **seventeen-drug** *E. coli* panel, and the seventeen are not the same. Between
2022 and 2023 **cefuroxime leaves and ceftriaxone joins**, confirmed against a hand-read of both tables. A check on
panel size would report nothing across that step. The panel check in `narsnet_validate.py` compares membership and
reports `drugs +['ceftriaxone']; drugs -['cefuroxime']`. The 2021 and 2022 panels, by contrast, are the same
seventeen molecules under different abbreviations — `Piperacillin/ Tazobactam` against `Pip-Taz` — and that step
comes out empty only because the names are normalised first.

### One repeated cell across two editions

The 2023 and 2024 *E. coli* tables print the same three figures for pus aspirate doxycycline: **2,080 tested, 41%,
CI 37.5–42.8**. Every other denominator in that column changes between the two editions; this is the only one that
does not. Both editions are carried exactly as printed and neither cell is flagged — a repeated figure is not by
itself a defect, and nothing in either report says which reading is intended. It is recorded here, and pinned in
`tests/test_narsnet_extraction.py`, so that it is a known property of the data rather than something a later reader
rediscovers and mistakes for an extraction fault.

These three editions also publish an interval for every cell, which is what makes any internal check possible at
all once the numerator column is gone.

Verbatim sample rows:

```
2019  E. coli, Table 6   (Number tested | Number Resistant | %R)
      Cefotaxime  18,183  14,219  78   3,310  2,641  80   1,030  841  82   13,843  10,701  77

2023  E. coli, Table 8   (Number Tested | %R | 95% CI)
      Meropenem   1907  36  34.3-38.7   6345  25  22.7-28.4   1187  29  26.2-31.4   19903  17  16.4-17.5

2024  E. coli, Table 8   (Number Tested (%R) 95% CI)
      Ampicillin  2278 (86) 85.0-87.8 | 8491 (89) 87.2-89.9 | 1490 (89) 87.5-90.7 | 30771 (87) 84.7-89.3
```

### Two further format facts

- **The metric is %Resistant, in every edition. %Susceptible is never printed.** This inverts the repo's current
  susceptibility-oriented schema (`susceptible_n`, `susceptible_pct`). V3 needs either a `resistant_*` parallel or an
  explicit `metric_direction` field — deriving %S as 100−%R would be **wrong**, because intermediate isolates are
  classified separately (methods describe three-way S/I/R) and are in neither figure.
- **No pooled all-specimen column from 2021 onward.** 2017–2019 carry a pooled column ("Blood+OSBF+PA+Urine");
  2020 has one for S. aureus only (`Blood + PA + OSBF, N=9,639`); 2021–2024 have none. A single national %R per
  antibiotic across all specimens is **not printed** in the recent editions and would have to be reconstructed by
  weighting — which is a derived quantity, not a reported one.

---

## A5. Structural differences affecting fair comparison

### The metric mismatch — parallel series, not a single joined value

NARS-Net publishes **%Resistant**; AMRSN publishes **%Susceptible**. Converting one to the other exactly would need
the intermediate fraction, and **AMRSN never publishes a %Intermediate value for E. coli or S. aureus** — not in
the yearly trend tables the repo's parsers read, not in a figure, not in narrative. The repo's own code records
this: `src/validate.py:106-107` notes that only for *P. aeruginosa* do the reports' susceptible and resistant
percentages sum to 100 (no intermediate category published), "which makes those conversions exact rather than
approximate" — the implication being that for E. coli, S. aureus and the rest, S + R ≠ 100 and the missing piece is
not printed. `data/processed/amr_trends.csv` carries `susceptible_n`, `tested_n`, `susceptible_pct` and no
resistant or intermediate column for any E. coli or S. aureus row.

**Consequence:** AMRSN %Resistant for E. coli and S. aureus cannot be computed. The two networks can be shown only
as **parallel series** — NARS-Net %R beside AMRSN %S — and must **never be joined on a single shared comparison
value**. Not publishing the intermediate fraction is ordinary reporting practice on both sides; this is a
constraint on the comparison, not a shortcoming of either body.

### Specimen mix — the biggest single confound

NARS-Net includes **five specimen types**: blood, urine, pus aspirate, other sterile body fluids (OSBF), and stool.

**Urine is included, and it is the largest stratum** — 46% of all specimens in 2023, with E. coli urine N=44,711 in
2024 versus blood N=3,621. AMRSN's main trend tables exclude urine. Since urinary isolates differ systematically in
susceptibility profile from bloodstream isolates, **a pooled NARS-Net figure compared against an AMRSN
non-urine figure would differ for reasons that have nothing to do with underlying resistance trends.**

The saving grace: **NARS-Net reports are stratified by specimen and never pooled** (2021 onward). So the defensible
construction is a **specimen-matched comparison** — most cleanly blood-only, or blood + pus aspirate + OSBF —
rather than any all-specimen figure. This should be a hard constraint in the V3 design, not a caveat in a footnote.

**Stool is restricted to enteric pathogens** (Salmonella Typhi/Paratyphi throughout; Shigella and V. cholerae from
2023). E. coli and S. aureus are never surveilled from stool, so there is no faecal-carriage or commensal E. coli
component to worry about. Stool volumes are trivial in early years anyway: 2 isolates in 2018, 1 in 2019 (excluded
from analysis), 10 in 2022.

### Case definition — similar in spirit, different in unit

Both networks count isolates rather than patients, but NARS-Net's dedup rule is explicit and specific:

> "For analysis, only the first antibiotic susceptibility result is considered for each patient per specimen type and
> pathogen… From each patient, only the first isolate of a given species isolated during the investigated time
> interval was included, regardless of its susceptibility profile." (2023 edition)

So the unit is **first isolate per patient × pathogen × specimen type** — neither raw isolates nor unique patients.
One patient can contribute several rows (different pathogens, or the same pathogen from different specimens).

Raw → deduplicated counts, where published:

| Year | Raw | Deduplicated | Removed |
|---|---|---|---|
| 2019 | 78,860 | 74,200 | 5.9% |
| 2020 | 57,282 | 55,688 | 2.8% |
| 2021 | 96,370 | 87,996 | 8.7% |
| 2022 | 128,529 | 119,686 | 6.9% |
| 2023 | 151,652 | 142,660 | 5.9% |
| 2024 | 206,745 | 195,077 | 5.6% |

**2017 and 2018 state a "unique patient" total but describe no deduplication rule at all** — no method, no raw counts.
The dedup procedure is first documented in 2019. So any trend crossing 2018→2019 compares numbers produced under an
undocumented method against a documented one. That is a factual observation about method documentation maturing over
time, and should be stated that way.

### Laboratory overlap between the networks — none found, and the reason is structural

All 20 publicly named ICMR-AMRSN institutions were checked against both the 70-entry NCDC network list
([amr.php](https://ncdc.mohfw.gov.in/includes/About/CentresAndDivision/amr.php)) and the authoritative 60-entry
parliamentary roster ([PIB, 28 Mar 2025](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2116222)).

**Zero institution-level overlap.** And the reason is not coincidence — the two networks recruit from **mutually
exclusive institutional strata**:

- **NARS-Net** is exclusively state government medical colleges and state/UT government institutes. The 2023 report
  states it directly: "*The data mentioned in this report is limited to Government hospitals, majorly Medical College
  Hospitals*". No private, corporate, mission or armed-forces hospital appears anywhere on the roster.
- **ICMR-AMRSN** is dominated by central institutes (AIIMS New Delhi, AIIMS Bhopal, AIIMS Jodhpur, PGIMER, JIPMER),
  private/corporate hospitals (Apollo Chennai, P.D. Hinduja Mumbai, Sir Ganga Ram Delhi, Tata Medical Center Kolkata),
  a mission hospital (CMC Vellore), a private trust college (MGIMS Sevagram) and armed forces (AFMC Pune).

The near-misses are same-city, different-institution pairs — PGIMER vs GMCH-32 in Chandigarh, JIPMER vs IGMC&RI in
Puducherry, SKIMS vs GMC Srinagar, NIMS vs Osmania in Hyderabad, AIIMS Bhopal vs Gandhi MC Bhopal.

This is a **stronger claim than "no overlap found"**, and it is worth stating as the positive finding it is: the two
networks sample structurally different slices of Indian tertiary care. That is also, incidentally, a plausible partial
explanation for any systematic difference in resistance rates, and belongs in the interpretation section.

**Three caveats to disclose rather than bury:**
1. ICMR names ~16–17 regional centres publicly but its reports reference up to RC21, so **~4–5 currently participating
   regional centres are not publicly named**. One could in principle be a state medical college also on NARS-Net.
2. ICMR de-identifies every data row as RC1…RC21, so **data-level overlap can never be checked** even for named
   centres. This is a permanent limitation, not a research gap.
3. NCDC's **state-level AMR networks** (Maharashtra, Kerala, Delhi, Gujarat, Rajasthan, Karnataka, MP, Telangana,
   Assam) funnel additional unenumerated medical colleges into NCDC's GLASS submission. Relevant only if GLASS figures
   are used — one more reason not to use them.

There is one real institutional linkage worth pre-empting, because a reviewer who knows the landscape will raise it:
NCDC states that 50 sites under its AMR programme are enrolled in the **ICMR-AIIMS Healthcare Associated Infections
surveillance project** ([haisindia.com](https://www.haisindia.com/)), using ICMR's definitions, SOPs and portal. That
is a different surveillance stream and does not compromise AMR-data independence — but disclosing it is better than
having it discovered.

### Other structural notes

- **Interpretive standard:** CLSI is the basis for classification in every edition that names one; EUCAST is not
  used to interpret results and is named just once, in the 2023 edition's methods text, as one of the
  "International Guidelines such as CLSI ... and EUCAST documents" the NARS-Net SOPs draw on. **The CLSI
  edition/year is unstated in every edition except 2024**, which specifies "M100 34th Ed.". The 2018 edition names
  no interpretive standard at all; the "CLSI document M02 and M100" citation first appears in the **2019** edition
  (for colistin broth microdilution only) and recurs through 2023.
- **Routine AST method** is first stated in 2019: Kirby-Bauer disc diffusion, with two of 21 sites using automated
  systems.
- **Site identification is inverted between the networks.** NARS-Net names its institutions in full (2018 onward,
  in an annexure); AMRSN codes its regional centres as RC1–RC21. The repo's existing RC-level de-identification
  handling therefore has **no counterpart on the NARS-Net side** — NARS-Net site-level data simply is not published
  at all, named or coded. Only national aggregates are.
- **Location strata** exist in NARS-Net (ICU / IPD / OPD, plus Emergency from 2021, clubbed with IPD in 2022's
  figures) — a dimension AMRSN also reports from 2023. Possible future cross-reference axis, out of scope for V3.

---

## A6. Machine-readable data — none exists

**There is no structured release of NARS-Net data anywhere.** Hand-extraction from the PDFs is genuinely necessary.

- **NCDC:** no portal, no dashboard, no API, no CSV/XLSX. The pipeline is deliberately offline — sites export a
  WHONET SQLite file, zip it, and **email it to `amrsurveillance@gmail.com`**
  ([WHONET guidance manual](https://ncdc.mohfw.gov.in/uploads/pdf/amr7.pdf)). Nothing public comes out of that chain
  but the report PDF and the semi-annual bulletins
  ([bulletin index](https://ncdc.mohfw.gov.in/amr-semi-annual-bulletin/), Issues 01–06, Jan 2023–Dec 2025).
- **data.gov.in:** no AMR or NCDC datasets found. ⚠️ **Soft negative** — the portal was displaying a maintenance
  banner and returned "No Result Found" even for known-good catalogues, so the index was likely broken. Worth one
  manual re-check before asserting this in print.
- **WHO GLASS:** India's data is in GLASS (enrolled 2017, submitting since 2018), but only as per-figure CSV
  downloads from the [Shiny dashboard](https://worldhealthorg.shinyapps.io/glass-dashboard/) (2016–2023) and PDF
  annex tables in the 2025 report. GLASS-AMR is **not** in the WHO GHO OData API. And as noted above, the GLASS
  submission covers a different population than the NARS-Net report.
- **Prior digitisation:** Shinde et al. (2026), *Frontiers in Antibiotics*, doi:10.3389/frabi.2026.1632790, extracted
  NARS-Net 2018–23 into heatmaps and tables but **deposited no data file** — worth emailing the authors.
  Leclerc's [GLASS2022 compilation](https://github.com/qleclerc/GLASS2022) (DOI 10.5281/zenodo.7486150) is clean and
  well-documented but its inclusion filter may exclude India — check `Iso3 == "IND"` before relying on it.
  ⚠️ A HuggingFace/Kaggle set named `amr-india-surveillance-2017-2024` exists — **do not use it**: it is
  AMRSN-derived rather than NARS-Net, unreviewed, self-cited, claims geocoded hospital locations for a network whose
  centres ICMR de-identifies, and ships a file literally named `amr_data_real.csv` alongside its others.

**So a clean, documented digitisation of the NARS-Net tables would be a genuine contribution — nobody has published one.**

---

## A7. Citation format

**No edition of the NARS-Net report carries a suggested-citation block, ISBN, DOI, or report number.** Checked in the
front matter of all eight. There are no named authors or editors. Published citations in the literature are
inconsistent on author form, title expansion, and year, and several contain now-dead URLs.

Printed publication dates exist for only two editions: **July 2022** (2021 report) and **July 2023** (2022 report).
No edition prints a city of publication except 2018 ("National Centre for Disease Control, Delhi, India").

Recommended Vancouver form, matching the repo's `CITATION.cff` conventions:

> National Centre for Disease Control. National Antimicrobial Resistance Surveillance Network (NARS-Net) annual
> report: reporting period January–December 2023 [Internet]. New Delhi: National Centre for Disease Control,
> Directorate General of Health Services, Ministry of Health and Family Welfare, Government of India; 2024
> [cited 2026 Sep 1]. Available from: https://ncdc.mohfw.gov.in/uploads/pdf/amr32.pdf

For `CITATION.cff`: `type: report`; corporate `name`-only author (not given/family); `institution:` the full DGHS/
MoHFW chain; `year:` the *publication* year, with the reporting period spelled out in the title to resolve the
cover-year ambiguity. **Leave `doi` and `isbn` unset** — inventing either would be wrong.

**Record `date-accessed` and archive every PDF** (Wayback or Zenodo). NCDC URLs have already migrated twice
(`ncdc.gov.in` → `ncdc.mohfw.gov.in`; `/WriteReadData/l892s/<digits>.pdf` → `/wp-content/uploads/YYYY/MM/<hash>.pdf`,
with `/uploads/pdf/amrNN.pdf` running in parallel), and citations published in 2022–2024 already point at dead links.
Treat the URL as ephemeral — this is exactly the failure mode V3's provenance fields should guard against.

---

# PART B — GAP ANALYSIS

What exists versus what V3 needs. Concrete items only.

## B1. Source documents

| Item | Status |
|---|---|
| NARS-Net 2017–2024 PDF URLs identified and verified reachable | ✅ Done (A3) |
| **NARS-Net PDFs downloaded into the local extraction pipeline** | ❌ **Not done — 8 PDFs to fetch** |
| ICMR AMRSN 2022/2023/2024 PDFs | ✅ Already held |
| NARS-Net semi-annual bulletins (Issues 01–06, 2023–2025) | ⬜ Not assessed — out of V3 scope unless intra-year granularity is wanted |
| Archival copies (Wayback/Zenodo) of all 8 NARS-Net PDFs | ❌ Not done — needed, given documented URL churn |

## B2. Scope questions — resolved

| Question | Answer |
|---|---|
| Are Klebsiella / Pseudomonas / Acinetobacter comparable? | ❌ **No** — genus-level in all 8 NARS-Net editions, species-level in AMRSN. Out of scope, confirmed. |
| Is there any species-level breakdown in an annex? | ❌ **No** — checked all 8 editions exhaustively |
| Which organisms are comparable? | ✅ **E. coli and S. aureus only** |
| Which years overlap both networks? | ✅ **2017–2024** for both (AMRSN historical tables 2017–2024; NARS-Net editions 2017–2024) |

## B3. Panel overlap — one input still missing

| Item | Status |
|---|---|
| NARS-Net E. coli panel, all 8 editions, as printed | ✅ Extracted (A2) |
| NARS-Net S. aureus panel, all 8 editions, as printed | ✅ Extracted (A2) |
| S. aureus overlap vs AMRSN 11-drug panel | ✅ **7 of 11** for 2021–2024; 6 of 11 for 2019–2020 |
| E. coli overlap vs AMRSN 10-drug panel | ✅ **7 of 10** for 2021–2024 (5 of 10 for 2017, 4 of 10 for 2018–2020), checked against the repo's actual `CANONICAL_PANEL`. `cefazolin` and `levofloxacin` are never in any NARS-Net E. coli panel; `ceftazidime` is in one in 2017 only |
| Drug-name normalisation map | ⚠️ **Variants catalogued (A2), mapping table not yet written** |

## B4. Schema changes V3 requires

| Gap | Detail |
|---|---|
| **Metric direction** | NARS-Net publishes **%Resistant only**; the repo's schema is susceptibility-oriented (`susceptible_n`, `susceptible_pct`). Needs a `metric_direction` field or parallel `resistant_*` columns. **%S must not be derived as 100−%R** — intermediates are classified separately and are in neither figure. |
| **Numerator absence** | `resistant_n` is **not printed for 2017–2018 or 2022–2024**; printed and usable for 2019–2020; for **2021** usable for S. aureus and for the E. coli PA/OSBF columns only (E. coli Blood column and two Urine cells are corrupt in the source). Needs a nullable numerator plus a status field distinguishing "not printed in source", "corrupt in source", and "zero". |
| **Reconciliation scope** | The repo's `pct_mismatch` check runs in full only on **2019–2020** NARS-Net rows, plus **2021** for S. aureus and for E. coli PA/OSBF. Needs an explicit `reconcilable` flag so the absence of a check is not mistaken for a passed check. |
| **Confidence intervals** | 2022–2024 print 95% CIs; AMRSN does not. New optional `ci_low` / `ci_high` fields. |
| **Specimen stratum** | NARS-Net rows are **per specimen type**, with no pooled column from 2021. Needs a `specimen` dimension — which AMRSN national rows do not have. This is the main schema divergence. |
| **Network / source dimension** | Every row needs `network` (`amrsn` \| `narsnet`) and NARS-Net's own `source_report_year` handled separately from cover-page year. |
| **Site-level data** | ❌ **Not available at all for NARS-Net** — only national aggregates are published. The repo's RC-level (V2) apparatus has no NARS-Net counterpart. V3 is national-level only. |

## B5. Known source-data issues to encode as flags

| Item | Status |
|---|---|
| 2017 Table 1 header says `Klebsiella pneumoniae`, rest of document says `Klebsiella species` | ⚠️ Documented — needs a flag if 2017 is ingested |
| 2019 ceftazidime appears in figures (Figs. 13–16) but not in Tables 6/7 | ⚠️ Documented — figure-only value, not table-extractable |
| **2021 E. coli Table 6, Blood column: `Number Resistant` does not reconcile** (e.g. Amikacin `1510 1088 29`; Ampicillin `1294 584 84`; Ciprofloxacin `1551 135 63`; Meropenem `854 981 25`, resistant > tested) | ✅ **Resolved by rendering the page.** The printed table itself is wrong — the Blood `Number Resistant` sub-column is corrupt at source, as are the Urine `Pip/Taz` and `TMP/SMX` cells (`Number Resistant` = `Number Tested`) and the Urine `Colistin` % (blank). The printed `%R` and `Number Tested` are sound; Pus Aspirate and OSBF columns reconcile; Klebsiella Table 7 Blood reconciles, so it is a one-table defect. Flag the affected cells; do not use the 2021 E. coli Blood numerator |
| 2023 Table 7 (Enterococcus): caption N=11,072 vs column headers summing to 14,705 | ⚠️ Flagged — out of V3 scope (Enterococcus), but indicates the 2023 edition has at least one caption/column inconsistency |
| 2023 Table 6 Linezolid blood row prints point estimate `0` with CI `0.1-0.4` | ✅ **Ingested and flagged** as `ci_excludes_point_estimate`. Refined by the cell-by-cell reading above: the percentage column is printed to whole numbers and the interval to one decimal, and the chapter gives the year's figure as 0.2%, which the interval brackets and which rounds to the printed 0 — a difference between two columns' rounding rather than a disagreement about the figure |
| **2022 Table 7, E. coli, OSBF doxycycline: 95% CI printed `24.2- 4.02`** | ✅ **Found during extraction and flagged** as `ci_bounds_inverted` and `ci_excludes_point_estimate`. The upper bound is printed below the lower, so the interval as printed is empty. Bounds are carried in the printed order and not swapped; no intended upper bound is reconstructed |
| 2018 report names **no interpretive standard** | ⚠️ Documented |
| CLSI edition unstated in all editions except 2024 (M100 34th Ed.) | ⚠️ Documented |
| 2022 ToC calls its annexure "…for the 2023 AMR Surveillance report" in a 2022-data report | ⚠️ Cosmetic, documented |

## B6. Verification still outstanding

| Item | Why it matters |
|---|---|
| ~~Visual inspection of 2021 E. coli Table 6 Blood column~~ | ✅ Done — see B5, and the cell-by-cell reading above. Blood `Number Resistant` is corrupt at source and not recoverable; `%R` and `Number Tested` are sound. Encoded as `CORRUPT_NUMERATORS`; 11 of the 13 cells fail, and the printed values are the column's own, displaced across rows |
| ~~2024 Annexure I, entries 11–54~~ | ✅ Done — full 54-site list read from `amr30.pdf`, recorded in `docs/narsnet_investigation_artifacts.md` |
| **2020 Fig. 1 site list** | Rendered as an image — 2020 site names are not text-extractable. Cosmetic unless the roster timeline is published |
| **ICMR-AMRSN Annexure I (full named participant list)** | Would close the ~4–5 unnamed regional centres and let the zero-overlap claim be stated without qualification. In `1725536060_annual_report_2023.pdf`, beyond the point where extraction truncated |
| **data.gov.in re-check** | Current negative was returned while the portal was in maintenance |
| **Contact Shinde et al. (2026)** | They digitised NARS-Net 2018–23; a shared file would provide an independent cross-check on extraction accuracy |

## B7. Not needed

- WHO GLASS data — different population (national + state networks), so not a valid substitute or cross-check.
- The HuggingFace/Kaggle `amr-india-surveillance-2017-2024` dataset — provenance failures listed in A6.
- Any site-level NARS-Net extraction — it does not exist in the published reports.

---

# PART C — READY-TO-PASTE PROMPT FOR CLAUDE CODE

Copy everything below the line into Claude Code, at the repo root.

---

```
V3 INVESTIGATION PHASE — NARS-Net cross-reference. Investigate and report only; write no extraction code yet.

## What V3 is

V1/V2 of this repo extract ICMR-AMRSN annual report data. V3 adds a cross-reference against a second, independent
Indian national AMR surveillance network: NCDC's NARS-Net. The goal is a factual, respectful comparison between two
legitimate national surveillance efforts — never a "which one is right" framing. Both networks' reconciliation gaps
and method changes are to be documented as ordinary features of large-scale multi-year surveillance data, fully and
specifically, with no vagueness and no softening of actual numbers, and with no language implying either body is
careless, secretive, or at fault. Match the register already established in this repo's docs.

## Step 1 — read the codebase first (do this before any source investigation)

Read and report back on, in this order:
- the extraction module(s) and how a report PDF becomes rows
- the row schema as actually implemented (field names, types, nullability), and how `computed_pct` is kept distinct
  from the printed percentage
- the flag vocabulary in use (`pct_mismatch`, `low_isolate_count_asterisk`, `panel_changed`, any others) and where
  flags are set
- how `source_report_year` and `source_table` are populated, and how the P. aeruginosa/piperacillin-tazobactam 2022
  cross-edition count revision is represented
- the test fixture conventions (all 129 tests) and how hand-verified fixtures are structured
- CITATION.cff, LICENSE, and the docs' tone conventions
- **the full 10-drug AMRSN Enterobacterales panel and the full 11-drug S. aureus panel, as drug-name strings actually
  used in the data** — I need the exact canonical spellings

Report what you found before moving on. Do not propose schema changes yet.

## Step 2 — known context (established research; do NOT re-derive any of this)

Eight NARS-Net annual reports, all verified live, text-extractable, no login:
  2017 https://ncdc.mohfw.gov.in/uploads/pdf/amr39.pdf
  2018 https://ncdc.mohfw.gov.in/uploads/pdf/amr38.pdf
  2019 https://ncdc.mohfw.gov.in/uploads/pdf/amr37.pdf
  2020 https://ncdc.mohfw.gov.in/uploads/pdf/amr36.pdf
  2021 https://ncdc.mohfw.gov.in/uploads/pdf/amr35.pdf
  2022 https://ncdc.mohfw.gov.in/uploads/pdf/amr34.pdf
  2023 https://ncdc.mohfw.gov.in/uploads/pdf/amr32.pdf
  2024 https://ncdc.mohfw.gov.in/uploads/pdf/amr30.pdf
Use the /uploads/pdf/ paths, not the /wp-content/ ones (the 2024 wp-content copy truncates before its annexure).
Cover-page years are unreliable: the 2019-data cover says "-2020", the 2020-data cover says "-2021". Index by
reporting period. wp-content/uploads/2024/03/87909365291642417515.pdf is a duplicate of the 2020 edition.

SCOPE, already settled: Klebsiella, Pseudomonas and Acinetobacter are reported at GENUS level ("Klebsiella species")
in all eight editions, with no species breakdown in any table, figure or annexure. AMRSN reports these at species
level. They are therefore NOT comparable and are out of V3 scope. E. coli and S. aureus are species-level in both
networks and are the primary comparable pair. (The one exception found: the 2017 edition's Table 1 column header
reads "Klebsiella pneumoniae" while Table 2 and results Table 6 in the same document say "Klebsiella species" — a
labelling inconsistency, not species data.) NARS-Net covered 7 pathogens 2017-2022; Shigella and V. cholerae were
added in 2023, making 9.

TABLE LOCATIONS (numbers are NOT stable — match on caption, fuzzily, since List-of-Tables and in-body captions
differ in several editions):
  E. coli:    2017 T5 | 2018 T6 | 2019 T6 | 2020 T8 | 2021 T6 | 2022 T7 | 2023 T8 | 2024 T8
  S. aureus:  2017 T4 | 2018 T4 | 2019 T4 | 2020 T5 | 2021 T4 | 2022 T5 | 2023 T6 | 2024 T6

DATA FORMAT — changes twice mid-series, this is the critical extraction fact:
  2017, 2018        "No. tested" + "% Resistance"                    → denominator only, no CI
  2019, 2020, 2021  "Number tested" + "Number Resistant" + "%R"      → NUMERATOR PRINTED, no CI
  2022, 2023, 2024  "Number Tested" + "(%R)" + "95% CI"              → denominator only, CI printed
Every edition prints %RESISTANT. %Susceptible is never printed in any edition. Do not derive %S as 100−%R:
intermediates are classified separately (S/I/R) and appear in neither figure.
Results are stratified by specimen type. 2017-2019 carry a pooled all-specimen column; 2020 has one for S. aureus
only; 2021-2024 have NO pooled column, so a single national %R across specimens is not printed anywhere.

PANELS as printed (E. coli): 2017 = 7 drugs; 2018 = 8; 2019 = 9; 2020 = 9; 2021 = 17; 2022 = 17 (same molecules as
2021, different abbreviations); 2023 = 17 but cefuroxime dropped and ceftriaxone added; 2024 = same as 2023.
PANELS as printed (S. aureus): 2017 = 9; 2018 = 10 (vancomycin present, n=14, footnoted low validity); 2019 = 8
(vancomycin and tetracycline removed); 2020 = 8; 2021 = 9 (teicoplanin added); 2022-2024 = same 9.
Oxacillin never appears in any edition — cefoxitin is the sole MRSA surrogate. Vancomycin is a printed row only in
2018; 2019/2020 state no site reported BMD MICs, 2022 reports screening in prose only.

NAMING VARIANTS needing normalisation (note the 2024 report is internally inconsistent — "TMP/SMX" in Table 6 but
"TMP-SMX" in Table 8, same document, so normalise per cell, not per edition):
  TMP/SMX | TMP-SMX | TMP / SMX | Trimethoprim/Sulfamethoxazole   → repo's "cotrimoxazole"
  Pip/Taz | Pip-Taz | Piperacillin/ Tazobactam                     → repo's "piperacillin-tazobactam"
  Amox/Clav | Amox-clav | Amox-Clav | Amoxicillin/ Clavulanic acid
  Gentamycin (2017) → Gentamicin (2018+)
Ceftazidime is in the AMRSN panel but appears in a NARS-Net E. coli table ONLY in 2017. In 2019 it appears in the
E. coli figures (Figs 13-14) but not in Table 6 — figure-only, not table-extractable.

STRUCTURAL CAVEATS that constrain any comparison:
- Urine is INCLUDED in NARS-Net and is its largest stratum (46% of specimens in 2023; E. coli urine N=44,711 vs
  blood N=3,621 in 2024). AMRSN's trend tables exclude urine. Because NARS-Net is specimen-stratified, the
  defensible construction is a SPECIMEN-MATCHED comparison — blood-only, or blood+pus aspirate+OSBF — never a
  pooled figure. Treat this as a hard design constraint.
- Stool is restricted to enteric pathogens; E. coli and S. aureus are never surveilled from stool.
- Dedup unit is first isolate per patient × pathogen × specimen type. Documented from 2019 onward; 2017 and 2018
  assert a "unique patient" total with no stated rule, so 2018→2019 crosses a method-documentation change.
- CLSI throughout, EUCAST never. Edition unstated except 2024 (M100 34th Ed.); 2018 names no standard at all. [Superseded by the investigation — see A5 "Interpretive standard": EUCAST is named once, in the 2023 methods text, among the international guidelines the SOPs draw on; it is not used to interpret results. Classification is CLSI in every edition that names one.]
- No institution-level overlap between the two networks: NARS-Net is exclusively state government medical colleges;
  AMRSN is dominated by central institutes, private/corporate and mission hospitals. Nearest cases are same-city,
  different-institution (PGIMER vs GMCH-32; JIPMER vs IGMC&RI). ~4-5 AMRSN regional centres are not publicly named,
  and AMRSN de-identifies all data rows as RC1-RC21, so data-level overlap can never be checked.
- NARS-Net publishes NATIONAL AGGREGATES ONLY. There is no site-level or state-level breakdown, named or coded.
  V3 has no counterpart to V2's RC-level work.
- No machine-readable release of NARS-Net data exists anywhere (no NCDC portal/API/CSV, nothing on data.gov.in,
  and WHO GLASS covers a different population — national plus state networks). PDF extraction is necessary.
- No edition carries a suggested citation, ISBN or DOI. NCDC URLs have migrated twice and published citations
  already contain dead links — archive the PDFs and record access dates.

## Step 3 — investigate the real source PDFs directly

Fetch and read the eight PDFs yourself. Verify rather than trust the summary above, and report concrete findings:

1. Confirm the table numbers and exact captions for the E. coli and S. aureus national tables in each edition.
2. Transcribe the exact column header structure per edition, and quote one full sample row per organism per edition.
3. Confirm exactly which editions print a numerator, and confirm no edition prints %Susceptible anywhere.
4. Produce the exact drug-name string list per organism per edition, and build a normalisation map from those
   strings to this repo's existing canonical drug names. Report the E. coli and S. aureus panel overlap counts
   against the repo's actual AMRSN panels (I have a provisional 7/11 for S. aureus and 7-of-8-named for E. coli —
   compute the real numbers from the repo's canonical lists).
5. DOUBLE-CHECK THE SCOPE DECISION: search every edition — including annexures, figure captions, footnotes and
   discussion — for any species-level breakdown of Klebsiella, Pseudomonas or Acinetobacter. If you find one
   anywhere, stop and report it, because it would widen V3's scope beyond E. coli and S. aureus. Report a clear
   negative if you find none.
6. Investigate the 2021 E. coli Table 6 Blood column: several rows do not reconcile (Amikacin "1510 1088 29";
   Ampicillin "1294 584 84"; Ciprofloxacin "1551 135 63"). Two independent fetchers returned identical values, so
   this looks like a PDF layout artefact rather than a read error. Determine whether the blood numerators are
   recoverable; if not, report exactly which cells are unusable.
7. Report the specimen column structure per edition (2020 merges pus aspirate and OSBF into one "PA + OSBF" column;
   2021 onward splits them into four columns), since this determines whether a specimen-matched join is even
   possible per year.

## Step 4 — report before building

Produce a written findings report covering: per-edition table locations and column structures; the drug-name
normalisation map; the real panel-overlap counts; which year-organism-drug-specimen combinations are actually
joinable against existing AMRSN data; which NARS-Net rows can support the repo's existing reconciliation check
(expected: 2019-2021 only) and which cannot; and a proposed set of schema additions and new flags — including how
to represent metric direction (%R vs %S), a nullable numerator that distinguishes "not printed in source" from
zero, the specimen dimension, and optional confidence intervals.

Do not write extraction code, do not modify the schema, and do not touch existing tests until I have reviewed that
report and confirmed the approach.
```
