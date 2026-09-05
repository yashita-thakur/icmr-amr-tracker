# Changelog

Every ingested report edition and every revised value found is logged here
(spec section 5).

## [Unreleased] — 0.4.0 (V3 — NARS-Net cross-reference)

V3 cross-references the ICMR AMRSN series against NCDC's **NARS-Net**, a second,
independent Indian national AMR surveillance network. Scope and constraints are
settled in `docs/narsnet_v3_research.md` and
`docs/narsnet_investigation_artifacts.md`.

**The standing constraint:** NARS-Net publishes **% resistant**, AMRSN publishes
**% susceptible**, and AMRSN publishes no % intermediate for *E. coli* or
*S. aureus* — so an AMRSN % resistant cannot be computed. The two networks are
presented as **parallel series** and are never joined on a single shared
comparison value.

### Added

- **`NARSNET_SOURCES` in `src/sources.py`** — all eight NARS-Net annual report
  editions (reporting periods 2017–2024), with NCDC URLs and SHA-256 hashes
  pinned as verified on 2026-09-01. A second registry rather than an extension of
  `SOURCES`: both are keyed by year and both cover 2022–2024, and keeping them
  apart also keeps the two networks' rows from ever being addressed as one
  series.
- **`ReportSource.network` and `ReportSource.cover_year`** — two optional fields,
  both defaulting to the V1 meaning. `cover_year` records a cover-page year that
  is *not* the reporting period: the edition covering January–December 2019 has
  a cover reading “AMR Annual report -2020”, and the 2020-data edition's reads
  “Annual Report-2021”. Everything is keyed and cited by reporting period; the
  discrepancy is carried in the data rather than resolved silently.
- **`src/fetch.py --network {amrsn,narsnet,all}`**, defaulting to `amrsn` so every
  pre-V3 invocation still means exactly what it did. Fetching and hash
  verification are now parameterised over a registry.
- **Strict hash checking for NARS-Net sources.** A changed hash on an AMRSN
  source warns and proceeds; on a NARS-Net source it rejects the download and
  leaves nothing on disk. The recorded table locations, captions and known source
  defects were established against the pinned bytes, so a re-upload invalidates
  the investigation and not merely the download. Keyed by network, never by
  hostname.
- `tests/test_narsnet_sources.py` — registry checks, including that the eight
  hashes still match those recorded in
  `docs/narsnet_investigation_artifacts.md`, and that the AMRSN registry is
  unchanged by the V3 edits. Test count 129 → 141.

- **`src/parsers/narsnet_antibiotics.py`** — a second antibiotic alias table,
  consulted before the shared one in `antibiotics.py`, which is not edited.
  `normalise_antibiotic` ends in a substring scan over every alias, so a key
  added to the shared table becomes a candidate substring for every AMRSN label
  too; a separate table leaves the AMRSN path unchanged by construction. Seven
  new keys cover the printed forms recorded in `docs/narsnet_v3_research.md` A2:
  `TMP/SMX`, `TMP-SMX`, `TMP / SMX`; `Pip/Taz`, `Pip-Taz`; the 2017 `Gentamycin`
  spelling; and `Ampicillin`, `Cefuroxime` and the four printed spellings of
  amoxicillin-clavulanate. Three canonical names are new, for drugs NARS-Net
  tests and AMRSN does not: `ampicillin`, `cefuroxime`,
  `amoxicillin-clavulanate`. `tests/test_narsnet_antibiotics.py` checks the
  no-drift guarantee in a subprocess that never imports the V3 module.
  Test count 141 → 202.
- **`NarsNetRecord` and `src/parsers/narsnet_parser.py`** — the schema and the
  extractor for the **2019 and 2020** editions, *E. coli* and *S. aureus*. Those
  two editions come first because they are the only ones printing a complete,
  usable numerator, so every cell can be checked against its own printed
  percentage before the geometry is pointed at editions that cannot be
  self-checked.
  - A separate dataclass, not an extension of `Record`. NARS-Net publishes
    **% resistant** and there is deliberately **no field meaning the same thing
    as `Record.susceptible_pct`**, so the two networks cannot be joined on a
    shared comparison value by accident.
  - `numerator_status` (`printed` / `not_printed_in_source` / `corrupt_in_source`)
    keeps "not printed" and "zero" apart, and `reconcilable` records whether the
    printed-percentage check could run at all, so an absent check is never
    mistaken for a passed one. `ci_low` / `ci_high` are carried for the 2022+
    editions and are null here. **No back-computed numerator field**: deriving
    one from denominator × %R would be the only invented count in the repo, and
    checking %R against it would be circular.
  - `specimen` uses distinct values for atomic strata (`blood`, `urine`,
    `pus_aspirate`, `osbf`) and composites, which name their constituents and
    are the only values containing `+`. The 2019 *E. coli* pooled column includes
    urine and the 2019 *S. aureus* one does not, so a single "pooled" label would
    have merged two different denominators.
  - A third table geometry: drugs down, specimen groups across, each split into
    `Number tested` / `Number Resistant` / `%R`. `base.py`'s `parse_measurement`
    does not apply — there is no `n / N (pct)` in a cell. Column centres are read
    from the sub-header row; rows are banded on their value words because the
    2019 edition prints each antibiotic label below its own value row.
  - Table location matches on caption **and shape**: every edition repeats its
    captions verbatim in a List of Tables, so a page qualifies only if it also
    carries at least two `%R` columns. This is also what keeps the 2020 edition's
    four-row "Overall resistance profile" summary from displacing its
    specimen-wise Table 5.
- `tests/test_narsnet_extraction.py` — **108 hand-read cells**, every printed
  cell in the four tables, read by eye off the rendered PDF pages rather than
  taken from `docs/narsnet_v3_research.md`, so a transcription slip in that
  document cannot propagate into the fixtures. Pages read: `narsnet_2019.pdf`
  p24 and p29, `narsnet_2020.pdf` p25 and p33. Test count 202 → 251.

### Changed

- **`Content-Type` is no longer a hard gate in `src/fetch.py`.** A publisher may
  serve a valid PDF as `application/octet-stream`, and refusing on that alone
  would reject a good file. The response type is now noted and the `%PDF-`
  magic-byte check decides.

- **`src/build_narsnet_dataset.py` and `src/narsnet_validate.py`** — the builder,
  the validator, and the first NARS-Net exports, for the 2019 and 2020 editions.
  - Exports land in `data/processed/` as **`narsnet_trends.{csv,json}`**,
    `narsnet_panel.json`, `narsnet_revisions.json` and
    `narsnet_extraction_report.json`. The filenames deliberately drop the `amr_`
    prefix the AMRSN exports carry: the two datasets share no comparison column
    and are not concatenable, and a reader with only the filenames should be able
    to tell that much.
  - **The cross-column check.** `find_degenerate_composite_disagreements` catches
    the case a within-cell check structurally cannot see: when a drug is reported
    for one specimen only and the other blocks are greyed out, a composite column
    and that single stratum describe the *same isolates*, so their counts must
    agree. In the 2019 *E. coli* table they do not — nitrofurantoin prints a
    denominator of 16,741 in both the pooled and urine columns and numerators of
    2,026 and 2,042. Both cells reconcile against their own printed percentage,
    so nothing inside a cell can find this. Both rows are flagged; both figures
    are kept as printed.
  - **`summarise_composite_sums` reports and does not flag.** Comparing a
    composite against the sum of the columns that partition it shows the
    difference is systematic, not exceptional: in 2019 every pooled denominator
    equals its partition sum exactly while no pooled numerator does (*E. coli*
    ciprofloxacin is +41), and in 2020 neither does. Flagging each row would mark
    nearly every composite row and bury the finding that is genuinely anomalous.
    The reports do not state that a pooled column is the arithmetic sum of the
    columns beside it, and the strata are separately de-duplicated. The measured
    differences are written to the extraction report instead, so their size can be
    judged rather than assumed.
  - **Panel *and* specimen-column change detection.** The two axes move
    independently. Between 2019 and 2020 the *E. coli* drug panel is identical
    while the pooled specimen column disappears, so a drug-only comparison would
    miss it and an edition-over-edition comparison of a pooled figure would be
    comparing against a column that is no longer printed.
  - **22 fixtures**, 20 of them narrative — the 2019 and 2020 chapters state a
    dozen specimen-stratified percentages in prose, naming the stratum each
    belongs to, and prose is written independently of the table it describes. Two
    fixtures record that the narrative corroborates the printed **%R** for cells
    whose printed counts do not (2020 *S. aureus* cefoxitin and ciprofloxacin,
    PA+OSBF), which is evidence about which of the two printed figures is stable.
  - **A partial build cannot overwrite the canonical exports.** `--year` and
    `--organism` narrow what is parsed, and before this guard existed a narrow
    build wrote all five canonical files with the subset it had. `export()` now
    refuses to write unless the records cover the whole `BUILD_YEARS x ORGANISMS`
    scope, prints why, and returns a non-zero exit. Completeness is derived from
    the records rather than the CLI arguments, so a parse that failed halfway is
    caught by the same guard. Refusing was chosen over writing to a `.partial`
    filename because it leaves nothing behind: no second set of paths to
    gitignore and no half-scope artefact to mistake for the dataset. The checks
    still run and still print, so a narrow build remains useful as a fast check.
  - `--organism` on the CLI, repeatable and validated against `SPECS`, matching
    how `--year` is validated against `BUILD_YEARS`.
  - `narsnet_revisions.json` is empty by design and carries a `note` saying why,
    as `rc_revisions.json` does. The check is a real one rather than a hardcoded
    empty list, so a future edition that did print a retrospective table would
    start returning rows instead of silently continuing to claim there is nothing
    to find.
- `tests/test_narsnet_validate.py` — 26 tests. The cross-column check is pinned
  from both directions: a composite in agreement is not reported, a partitioned
  composite is not treated as degenerate, and a composite whose denominator
  differs from its stratum's is not claimed as a finding at all. Also asserts the
  committed export matches a fresh parse, so a stale export fails the suite.
  Test count 251 → 281.

- **The 2021 edition**, *E. coli* and *S. aureus* — `BUILD_YEARS` becomes
  `[2021, 2020, 2019]` and the dataset goes from 108 rows to 192. This is the
  last edition that prints a numerator; 2022–2024 replace it with a 95% CI.
  - **`numerator_status` gains its third value, `corrupt_in_source`.** The 2021
    *E. coli* Table 6 prints a Blood `Number Resistant` sub-column, and two
    Urine cells, whose figures are not those cells' numerators — meropenem
    prints 981 resistant of 854 tested, and the two Urine cells print a
    numerator equal to their denominator beside a percentage that is not 100.
    A third enum value rather than a flag on top of `printed`, for the reason
    `not_printed_in_source` is also a value: consumers switch on this field to
    decide whether they may use `resistant_n`, and a two-value field plus a flag
    lets a consumer that did not know about the flag read an unusable number as
    a usable one. `reconcilable` is now `numerator_status == printed and
    tested_n`, so it says the printed number can be trusted as this cell's
    numerator rather than merely that one exists, and no `computed_pct` is
    derived from a corrupt cell.
  - **Which cells are corrupt is declared, not inferred.** `CORRUPT_NUMERATORS`
    records the two blocks from a hand-read of the printed page. A rule keyed to
    the size of the disagreement would have swept in the 2020 *S. aureus*
    doxycycline Blood cell, which is a `pct_mismatch` — a cell whose own
    numerator disagrees with its own percentage — and is a different finding
    recorded a different way. The two are kept apart in the extraction report
    for the same reason.
  - **The whole Blood sub-column is declared, including the two cells that
    agree.** Amoxicillin-clavulanate prints 390 of 680 beside 57, and colistin 0
    of 914 beside 0. Both reconcile, and both are still marked corrupt: taking
    each Blood row's printed denominator and percentage and asking which printed
    numerator satisfies it yields a one-to-one matching in which twelve of the
    thirteen values belong to a different row of the same column, so the two
    that agree are the two the displacement left in place. Which values came to
    rest on their own row is not something the printed table lets a reader
    establish, so the sub-column is the unit. `summarise_corrupt_numerators`
    counts the agreements into the extraction report rather than exempting them,
    so the judgement is stated where it can be argued with. The full matching is
    in `docs/narsnet_v3_research.md`; **it is not used to repair anything.**
  - **Column geometry now comes from the ruled grid**, with the sub-header words
    used only to name each column. The 2021 sub-headers are rotated a quarter
    turn and sit wherever their cell leaves room — far enough off centre in the
    narrower columns to fall closer to a neighbour than to their own, which
    silently dropped cells under the previous nearest-centre rule. Two grid
    artefacts are handled explicitly: a rule drawn as two strokes leaves a
    sliver that holds no value word and is not a column, and a merged header
    cell contains the columns beneath it and is not one either. What survives
    must be one row-label column plus a whole number of three-column specimen
    groups, or the parser stops. The 2019 and 2020 cells are byte-identical
    under the new geometry.
  - Rotated words also read backwards — pdfplumber orders characters top-down,
    so `Number` arrives as `rebmuN` — which `_text` reverses. The percentage
    column is renamed in this edition (`Resistance (%)` for *S. aureus*,
    `Resistance %` for *E. coli*), so it is now recognised by its percent sign
    rather than by the literal `%R`. The *S. aureus* caption reads "Resistance
    profile **observed in**" where the *E. coli* one in the same document reads
    "of".
  - `specimen_key` learns the spelled-out headings this edition uses,
    `Pus Aspirate` and `Other Sterile Body Fluids`, matched as phrases before
    the word-by-word pass so that four words cannot be read as four strata. The
    2021 edition prints no pooled column and splits PA+OSBF into two, so **no
    2021 specimen column has the same membership as any 2020 one** and there is
    no pair to compare edition over edition. The panel check reports both axes
    moving at the same step: eight drugs added to the *E. coli* panel,
    teicoplanin to *S. aureus*.
  - **18 new fixtures**, 40 in total; 14 of the 18 are narrative. The 2021 chapters
    state the *E. coli* Blood percentages for ciprofloxacin, TMP/SMX and
    piperacillin-tazobactam, and carbapenem resistance in blood "up to 33%" —
    four of the thirteen cells whose numerator is unusable. Prose is written
    independently of the table, so those four percentages are corroborated from
    outside it. Each fixture's `note` records whether the figure came from the
    table or the narrative, and where both, which part came from which.
- `tests/test_narsnet_extraction.py` — **84 more hand-read cells**, 192 in
  total, read by eye off `narsnet_2021.pdf` p24 and p29 before being compared
  against `docs/narsnet_v3_research.md`, so the reading is evidence for that
  document's B5 entry rather than a copy of it. That reading refines B5: the
  Blood sub-column fails in 11 of 13 cells, not all 13. With the corrupt-
  numerator tests in `tests/test_narsnet_validate.py`, test count 281 → 311.

- **The 2022, 2023 and 2024 editions**, *E. coli* and *S. aureus*, as one group
  — `BUILD_YEARS` becomes `[2024, 2023, 2022, 2021, 2020, 2019]` and the dataset
  goes from 192 rows to 450. These three print `Number Tested`, a percentage and
  a **95% confidence interval**, and no numerator at all.
  - **`numerator_status` is `not_printed_in_source` on all 258 rows**, with
    `reconcilable` false, no `resistant_n` and no `computed_pct`. **No numerator
    is back-computed** as denominator × %R: it would be the only invented count
    in the repository, and checking the percentage against it would be circular.
    The dataset therefore has three editions that can be checked against their
    own counts and three that cannot, and `reconcilable` is what tells them
    apart — an absent check is never mistaken for a passed one.
  - **`ci_excludes_point_estimate`, the check these editions can support.** With
    no numerator there is no second figure inside a cell for the percentage to
    disagree with, but a percentage and a confidence interval are two printed
    statements about one quantity and can disagree on their own. **Two cells of
    258** sit outside their own interval, and `summarise_ci_checks` reports the
    distance to the nearer bound and whether it is within half the precision the
    percentage is printed to, because the two are not the same kind of finding.
    - 2023 *S. aureus* linezolid, blood: 4,896 tested, a point estimate of 0
      against an interval of 0.1–0.4. The percentage column is printed to whole
      numbers and the interval to one decimal, and the 2023 chapter gives the
      year's figure as 0.2%, which the interval brackets and which rounds to the
      printed 0. The check catches a difference between how two columns are
      rounded; the underlying figures agree. `docs/narsnet_v3_research.md` B5
      previously recorded this row as internally inconsistent and now records
      the narrower reading.
    - 2022 *E. coli* doxycycline, OSBF: 139 tested, 32%, interval printed
      `24.2- 4.02`. The upper bound is printed below the lower, so the interval
      as printed is empty. **Bounds are carried in the printed order and not
      swapped**, and no intended upper bound is reconstructed. Also flagged
      `ci_bounds_inverted`, because "outside its interval" understates an
      interval whose ends are the wrong way round. Found during extraction; it
      was not previously recorded.
  - **Two sources of column geometry, chosen by what the page shows.** The ruled
    grid divides each specimen group into its three columns in 2019–2022 but not
    in 2023 and 2024, which rule the group boundaries and nothing inside them.
    Where the grid yields one row-label column plus a whole number of groups it
    is used; where it does not, the sub-columns are read from the sub-header
    words instead — and only when those words are horizontal, since a rotated
    sub-header says nothing about where its column is. A table that satisfies
    neither stops the parser rather than being guessed at. The 2019–2021 rows
    are unchanged.
  - The percentage column is bracketed in these editions and the 2022 *E. coli*
    table prints it `(% R)`, which arrives as two words, so brackets are
    stripped before the sub-header lookup. A confidence interval printed with a
    space after its dash — `31.2- 38.2` — is two words of one cell and is
    rejoined; reading only the first would have silently lost every upper bound
    printed that way.
  - **Panel membership, not panel size.** 2022, 2023 and 2024 each print a
    seventeen-drug *E. coli* panel and the seventeen are not the same: between
    2022 and 2023 **cefuroxime leaves and ceftriaxone joins**. A check on panel
    size reports nothing across that step; the panel check compares membership
    and reports the swap. The 2021 and 2022 panels are the same seventeen
    molecules under different abbreviations, and that step comes out empty only
    because the names are normalised first.
  - From 2022 the reports print `x` where a drug is not tested for a specimen,
    with a footnote saying so, rather than greying the block. Nothing was
    measured, so nothing is emitted — the same treatment a greyed block gets in
    the earlier editions.
  - **A repeated cell, recorded and not flagged.** The 2023 and 2024 *E. coli*
    tables print the same three figures for pus aspirate doxycycline — 2,080
    tested, 41%, CI 37.5–42.8 — and it is the only denominator in that column
    unchanged between the two editions. Both are carried as printed. A repeated
    figure is not by itself a defect and neither report says which reading is
    intended, so it is pinned in the tests and described in the research doc
    rather than flagged.
  - **20 new fixtures**, 60 in total, 51 of them narrative. From 2022 the
    chapters quote the confidence interval alongside the percentage, so
    `NarsNetFixture` gained `expected_ci_low` and `expected_ci_high` and a
    narrative fixture for these editions corroborates both figures from outside
    the table. Each fixture's `note` records whether the figure came from the
    table or the narrative, and where both, which part came from which.
- `tests/test_narsnet_extraction.py` — **258 more hand-read cells**, 450 in
  total, in a second dictionary `HAND_READ_CI` because these editions do not
  print the same columns. Pages read: `narsnet_2022.pdf` p36 and p44,
  `narsnet_2023.pdf` p30 and p38, `narsnet_2024.pdf` p25 and p34, all read
  before being compared against `docs/narsnet_v3_research.md`. Test count
  311 → 340.

- **The 2017 and 2018 editions**, *E. coli* and *S. aureus* — `BUILD_YEARS`
  becomes `[2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017]` and the dataset
  goes from 450 rows to 558. All eight NARS-Net reporting periods are now
  covered. These two print a denominator and a percentage and nothing else.
  - **No check inside a cell reaches either edition, and the dataset says so.**
    There is no numerator for the percentage to be reconciled against and no
    interval for it to fall outside of, so all 108 of those rows carry
    `numerator_status = not_printed_in_source`, `reconcilable = false`, no
    `resistant_n`, no `ci_low` and no `ci_high`, and neither
    `printed_pct_vs_printed_counts` nor `printed_pct_vs_printed_ci` can ever
    contain one. The parser docstring, `DATA_LICENSE.md` and a new
    `editions_no_check_reaches` field in `narsnet_extraction_report.json` all
    state it in those words. This module previously stopped at 2019 on exactly
    this ground; extending to them does not answer the objection, it moves who
    has to know about it, and the objection is carried forward rather than
    dropped.
  - **`no_internal_check_possible`, a flag on the row.** Whether a cell was
    checked was previously answerable only from `reconcilable`, and
    `reconcilable` does not answer it. It says whether the printed numerator can
    be trusted as that cell's numerator, and the two questions come apart in
    both directions: it is false on all 258 rows of 2022-2024, and those rows
    ARE checked, against their own interval; and it is true on the 2021
    *E. coli* urine colistin row, whose numerator is printed and sound and which
    is checked against nothing, because that cell's percentage column is blank.
    All four combinations of the two occur in the dataset, so neither value of
    `reconcilable` implies either answer.

    The flag is raised where neither comparison had two printed figures to work
    with, and is derived per cell from what the cell prints rather than from its
    edition — a flag keyed on the year would be a year lookup wearing the name
    of a fact about the cell, and would miss seventeen rows. It lands on 125
    cells in four editions for three reasons: all 108 rows of 2017 and 2018,
    which print no numerator and no interval; the fifteen 2021 cells whose
    printed numerator is not that cell's, which leaves the percentage nothing to
    disagree with; and two cells that print no percentage at all — 2020
    *E. coli* nitrofurantoin PA+OSBF, and the colistin row above.
    `summarise_unchecked_cells` breaks it down by edition and reason into
    `cells_no_internal_check_reaches` in the extraction report, naming the
    seventeen rows outside 2017 and 2018 individually, since those are the ones
    a reader who knows only which editions print what would not predict.
  - **The back-computed numerator the research doc suggested was not taken.**
    `docs/narsnet_v3_research.md` proposed recovering an approximate numerator
    as denominator × %R and labelling it derived. It would be the only invented
    count in the repository, and a percentage checked against a numerator
    computed from that same percentage cannot disagree with it, so the check it
    appears to buy is empty. The doc now records the decision.
  - **26 new fixtures**, 86 in total. Twenty-one of the twenty-six are every
    specimen-stratified percentage the two chapters state — all of them, not a
    sample, because here the prose is the only independent statement about those
    rows there is. Each carries the denominator hand-read from the cell beside
    it, so the two provenances corroborate each other. Four name no stratum and
    are pinned on the column that prints the figure, with the note saying so
    where more than one column does. The 2018 chapter also restates three 2017
    figures — blood cefoxitin as 57%, blood ertapenem and imipenem as 37% and
    25%, against a 2017 table printing 57.1, 36.7 and 25.2 — which is the only
    place in the series where one edition says anything about another's numbers.
  - **A third column layout, two wide.** `NO_NUMERATOR_SHAPE` joins
    `COUNT_SHAPE` and `CI_SHAPE`, and the group scan now tries the widest layout
    first at each position: the first two columns of a 2022–2024 group are
    `tested` then `pct`, which is the whole of the new layout, so a scan trying
    the shorter width first would halve every one of those groups and orphan its
    interval.
  - **A count column named only `Number`.** The 2018 sub-header stops there,
    having no numerator to distinguish it from. `Number` cannot join the words
    that name a column — it opens both `Number tested` and `Number Resistant` in
    2019–2021, so it does not say which — and is read as a last resort instead,
    naming a column only where no other sub-header word reaches it. True of the
    2018 tables and of no other edition. The research doc recorded 2017 and 2018
    as sharing the 2017 sub-header wording; they do not, and it is corrected.
  - **Percentages printed with their sign.** The 2018 tables print `63%` where
    every other edition prints `63`. Not previously recorded anywhere.
  - **Tables end at the last rule that runs their full width**, not at
    pdfplumber's bounding box. In the 2017 *S. aureus* table and both 2018
    tables that box reaches about ten points past the last full-width rule and
    takes in the abbreviation footnote below. Read as content, one line of
    footnote does three unrelated-looking kinds of damage: its "tested" is taken
    for a column heading and puts the bottom of the sub-header below the bottom
    of the data, leaving no data rows at all; its "Pus" holds a sliver between
    two rules open as a column; and its opening words land in the last data
    row's antibiotic label. The other thirteen tables already end at that rule.
  - **Rows are banded on whether their words overlap vertically**, not on a grid
    of fixed-height buckets. The two halves of a printed row are two or three
    tenths of a point apart everywhere in the series, and a fixed grid splits a
    row whenever those tenths fall either side of a bucket edge. Two rows do:
    2018 *S. aureus* linezolid, counts at y=321.9 and percentages at 322.1, and
    2018 *E. coli* trimethoprim/sulfamethoxazole at 554.0 and 554.2. Split, each
    lost its denominators to a band of its own and kept only its percentages.
    The grid had worked on the 2019–2024 tables by coincidence.
  - **The table is bound to its caption**, not taken as the largest ruled table
    on the page. The 2018 *S. aureus* table shares its page with the
    *Enterococcus* table, both full-width, ruled alike and within a tenth of
    each other in area; picking by area gets the right one there for a reason
    that has nothing to do with which table the caption is over. Across all
    sixteen tables the caption rule picks the same table the area rule did.
  - **A second caption grammar.** 2017 and 2018 write "Resistance (%) in *X*"
    where every later edition writes "Resistance profile of" or "observed in".
    The older form is the looser of the two and matches every pathogen's table
    in those editions; it was checked against every caption in all eight
    editions that it adds exactly the four tables intended and nothing in
    2019–2024.
  - **A partition sum of nothing is now reported as null, not 0.**
    `summarise_composite_sums` summed the printed numerators of a composite's
    parts and rendered an empty sum as zero, which put a count in the extraction
    report that the page never printed, beside a null composite — reading as a
    pooled column disagreeing with its parts by its whole size. It changes 26 of
    the 50 rows in that block, all of them in 2017 and 2018, from
    `partition_resistant_sum: 0` to `null`. **It corrects nothing already
    committed:** no edition from 2021 on prints a pooled column at all, so that
    block held 24 rows before this commit, every one of them 2019 or 2020 and
    every one with printed numerators. The bug was reachable only by the
    editions this commit adds.
  - **The unused `_NUMBER_RE` constant is removed.** A regex defined in
    `narsnet_parser.py` and referenced nowhere in the repository, tests
    included. It predates this work; it is deleted here rather than left for a
    later reader to wonder which of the three value regexes is the live one.
  - **Verified on the six earlier editions.** Running HEAD's parser and this one
    over the same PDFs produces the same 450 records: the same set of keys, and
    every field identical except `flags` on seventeen rows, which gain
    `no_internal_check_possible` and lose nothing. Across the six geometry
    changes alone the output was byte-identical to HEAD at
    `90645bb5704a90ca52d1e52353508ef7073b37e5b4bb04a9b7fbc2431b29b1df`; the flag
    is the one intended change to those editions, and it takes the hash to
    `e0d30511b8fd33bc9a6e1ae81f0b19d0258cde245bece82b41894bd4f84b563c`.
- `tests/test_narsnet_extraction.py` — **108 more hand-read cells**, 558 in
  total, in a third dictionary `HAND_READ_PCT` because these editions do not
  print the same columns as either other group. Pages read: `narsnet_2017.pdf`
  p6 and p7, `narsnet_2018.pdf` p7 and p10, all read before being compared
  against `docs/narsnet_v3_research.md`. That dictionary carries more weight
  than the other two: the 2019–2024 cells are checked against something printed
  beside them as well, and these have nothing. Test count 340 → 376.

### Fixed — the four deferred statements

`data/processed/` now carries NARS-Net rows, so the four statements recorded
below as deferred have been corrected in this commit. Each described the project
as carrying ICMR AMRSN data and nothing else:

- **`ATTRIBUTION` in `src/sources.py`** now names both networks and disclaims
  affiliation with both ICMR and NCDC. It is written into every export file, so
  this is the correction with the widest reach. See the note below on the AMRSN
  export files. Its NARS-Net range reads 2017–2024 now that all eight editions
  are ingested, and `DATA_LICENSE.md` quotes the same string.
- **`index.html`** — the “This is not” list now reads “a pooled cross-network
  figure” rather than “NARS-Net data”, and says NARS-Net is carried as a separate
  parallel series in its own files.
- **`README.md`** — the same correction, plus the reason the two can never be
  combined: they do not share a comparison value.
- **`DATA_LICENSE.md`** — the source-material, project-claim, required-attribution,
  disclaimer and “what this data is NOT” sections. The source-material section now
  records that the NARS-Net reports carry no copyright notice, ISBN or DOI that
  this project has found, and states plainly that absence of a notice is not a
  grant of rights, so the same conservative position is taken for both bodies.

**Note on the AMRSN export files.** `amr_trends.json`, `revisions.json`,
`extraction_report.json`, `amr_rc_trends.json`, `rc_revisions.json`,
`rc_panel.json` and `rc_extraction_report.json` embed the ATTRIBUTION string at
the moment they are generated, and they were **not** rebuilt in this commit. They
therefore still carry the previous single-network wording (“Derived from publicly
available ICMR AMRSN annual reports (2017–2024) … not endorsed by or affiliated
with ICMR”). **This is intentional, not an inconsistency left behind.** Those
files contain AMRSN rows and nothing else, so the single-network wording is
accurate for their contents; rebuilding them purely to restate the attribution
would rewrite the `extracted_date` on every AMRSN row and produce a large diff
that changes no data. They will pick up the two-network wording the next time the
AMRSN pipeline is run for a reason of its own. `narsnet_*.json`, generated in this
commit, carries the corrected two-network wording.

### Deferred to the commit that first writes NARS-Net rows

Four published statements describe this project as carrying ICMR AMRSN data and
nothing else. Each is still accurate — no NARS-Net data has been extracted yet
— and each becomes false the moment `data/processed/` carries a NARS-Net row.
They are therefore corrected in that same commit, not in a later docs pass:

- **`ATTRIBUTION` in `src/sources.py`** — credits ICMR AMRSN only and disclaims
  affiliation with ICMR only. It must name both networks and disclaim affiliation
  with both NCDC and ICMR. This is the widest-reaching of the four: it is written
  into every export file and every generated figure.
- **`index.html`** — the “This is not” list: “NARS-Net data. AMRSN and NCDC's
  NARS-Net are different networks and are never pooled here.”
- **`README.md`** — “**Not NARS-Net.** … This repository contains AMRSN data
  only.”
- **`DATA_LICENSE.md`** — more than one line: the source-material, required-
  attribution and disclaimer sections all describe the ICMR AMRSN reports as the
  only source documents, and the “what this data is NOT” list treats NARS-Net as
  external to the dataset. The licence position on the NCDC PDFs is a separate
  question and is not settled here.

### Source findings (V3, from the investigation)

- **No cross-edition revision detection is possible for NARS-Net.** Each edition
  reports only its own reporting period, with no retrospective multi-year table,
  across all eight editions. A V3 revisions file is structurally empty by design,
  the same as `rc_revisions.json`, and will carry a `note` field saying so.
- **The 2019 and 2020 editions do not reconcile quite completely.** The
  investigation recorded these two as the editions that reconcile in full.
  Extraction finds **8 cells of 108 where the printed percentage does not follow
  from the printed counts**. Seven sit just past the half-point of the printed
  precision (for example 2020 *E. coli* ampicillin PA+OSBF, 2,291 of 2,590 =
  88.5%, printed 89) — the source rounding a percentage it did not compute from
  the counts it printed. The eighth is a different kind: **2020 *S. aureus*,
  doxycycline, blood — 24 resistant of 2,638 tested, printed as 12%**. All eight
  carry `pct_mismatch` and are kept exactly as printed. This narrows the
  reconciliation claim in `docs/narsnet_v3_research.md` A4; that document is
  otherwise unchanged.
- **2019 *E. coli*, nitrofurantoin: the pooled and urine columns disagree.** Both
  print a denominator of 16,741 for what must be the same isolates — the drug is
  reported for urine only, with the blood and PA+OSBF blocks greyed out — but the
  pooled column prints 2,026 resistant against the urine column's 2,042. Both
  round to 12%. This is a cross-column check rather than a within-cell one, so it
  is recorded here rather than flagged on a row; the validator is not built yet.
- **The `/uploads/pdf/amrNN.pdf` paths are the ones to use.** The `/wp-content/`
  copies also resolve, but the 2024 one truncates before Annexure I.
  `wp-content/uploads/2024/03/87909365291642417515.pdf` is a duplicate of the
  2020 edition, not a distinct year.
- **NCDC URLs have already migrated twice** and published citations of these
  reports already contain dead links, which is what the pinned hashes and the
  recorded access date guard against.

## 0.3.0 — 2026-09-01 (V2 — Regional Centre breakdowns)

### Added

- **Regional Centre (RC) breakdown dataset**, in its own schema and files,
  kept separate from `amr_trends.csv` because the RC-wise tables are single-year
  cross-sections with a different shape and much narrower organism coverage:
  - `data/processed/amr_rc_trends.{csv,json}` — one row per organism × Regional
    Centre × antibiotic × edition. V1's provenance fields
    (`source_report_year`, `source_table`, `source_url`) plus `regional_centre`.
    **1,365 rows.**
  - `data/processed/rc_panel.json` — per organism, the RC set each edition
    printed and how it differs from that organism's earliest edition.
  - `data/processed/rc_revisions.json` — cross-edition revision check; near
    empty by design (see below), with a `note` field saying so.
  - `data/processed/rc_extraction_report.json` — sources, hashes, what parsed,
    what was skipped as having no such table that edition.
- `src/parsers/rc_parser.py` — locates RC-wise tables by caption meaning, never
  table number, the same as `base.py`. Reuses `base.py`'s cell grammar,
  whole-word assembly and printed-vs-computed check. The axis differs (columns
  are antibiotics, rows are Regional Centres), so column and row geometry are
  derived here: column centres from the data grid's `n / N` tokens (the header
  wraps across up to four lines and is unreliable for geometry), and each row is
  banded on its own numerator line so a tall wrapped cell cannot hand its
  percentage to the next RC.
- `src/build_rc_dataset.py`; `src/rc_validate.py` (10 hand-verified RC-cell
  fixtures, RC panel-change detection, the RC revision guard);
  `tests/test_rc_extraction.py` and `tests/test_rc_panel.py`. Test count 83 → 129.
- **`rc_panel_changed(baseline=…,added=[…],dropped=[…])` flag** on every row
  from an edition whose RC set differs from that organism's earliest edition —
  applied instead of averaging across a panel that changed between editions.

### Source findings (V2)

- **RC-wise AMS coverage is much narrower than the national tables.** Only
  *E. coli*, *K. pneumoniae* and *S. aureus* have an RC-wise susceptibility
  table for the non-urine population. *A. baumannii*, *P. aeruginosa* and MRSA
  have none in any edition. *E. coli* / *K. pneumoniae* have one only from the
  2023 edition on — the 2022 edition breaks them down by RC for *urine*
  isolates only, out of scope exactly as for V1.
- **Table numbers move, as ever.** *E. coli*: Table 3.10 (2023) → 2.10 (2024).
  *K. pneumoniae*: 3.11 → 2.11. *S. aureus*: 6.3 (2022) → 7.3 (2023) → 6.3
  (2024).
- **Two caption grammars.** "… Percentage RC wise of *X* …" (2022/2023) and
  "RC-wise … percentages of *X* …" (2024). Both carry the tokens "RC wise" /
  "RC-wise" and "(AMS)"; that pair separates them from the national trend
  captions and from the "Regional centre wise distribution" isolate-count
  tables.
- **The Enterobacterales RC panel is one drug shorter** — 9, not the national
  10: cefazolin is absent from the RC-wise tables.
- **The RC panel is not stable across editions, and the codes carry no key.**
  `RC1`…`RC21` are de-identified in the reports and the tables carry no
  code-to-institution key, so an RC cannot be assumed to be the same laboratory
  across editions. The set also
  moves: **`RC15` is absent from every 2024 table** (all three organisms)
  though present in 2022/2023; **`RC18` is absent from *S. aureus* in 2023 and
  2024**, and the 2024 *S. aureus* table also omits `RC1`. The 2024
  participating-centres annexure additionally adds two hospitals (Artemis and
  Fortis, Gurugram) not in the 2022/2023 network.

### Reconciling printed values (V2)

In the **2023 edition**, three RC cells print a susceptibility of 0% where the
cell's own counts would round differently. Carried as printed and flagged
`pct_mismatch` — the same policy as V1: report what the table shows, leave
reconciliation to the reader.

- ***K. pneumoniae* / RC7 / levofloxacin** (Table 3.11): `1 / 16` printed
  `(0)`; the ratio is 6.25%.
- ***S. aureus* / RC2 / tigecycline** (Table 7.3): `2 / 3` printed `(0)`.
- ***S. aureus* / RC3 / teicoplanin** (Table 7.3): `1 / 1` printed `(0)`.

### Why RC cross-edition revision detection is (almost) empty

The RC-wise tables are single-year cross-sections: each edition reports its own
year only, with no retrospective trend axis. No `(organism, RC, antibiotic,
year)` key is covered by more than one edition, so the V1 revision detector —
kept and run for V2 as `find_rc_cross_report_revisions` — has essentially
nothing to compare and returns an empty list on the 2022–2024 data. This is
**by design**, not an incomplete feature; `rc_revisions.json` says the same in
its `note` field. Contrast `revisions.json`, where every calendar year is
covered up to three times.

## [Unreleased] — 0.2.0 (V1.1)

### Added
- Four more organisms across two more chapters: *Acinetobacter baumannii* and
  *Pseudomonas aeruginosa* (non-fermenting Gram-negative bacilli), and
  *Staphylococcus aureus* and MRSA (staphylococci).
- Dataset grows from 420 to **1,286 rows**; fixtures from 28 to **41**; tests
  from 64 to **83**.
- Parsing was refactored rather than duplicated: `parsers/trend_parser.py` now
  drives every chapter, with per-chapter modules supplying only configuration
  (organism spelling, specimen wording, expected panel). The hardened
  behaviours therefore protect all six organisms, and each new trap found below
  was fixed once.
- `parsers/antibiotics.py` holds one canonical drug-name registry, matched
  longest-alias-first so `trimethoprim-sulfamethoxazole` cannot be captured by
  `trimethoprim`.
- Page text is memoised per (file, page) while locating captions. Without it,
  six organisms re-extracted the same pages six times over and a full build
  took minutes.

### Source findings (V1.1)

- **Caption grammar differs by chapter.** Three variants exist, and a parser
  written for the Enterobacterales wording finds *nothing* in the others:
  `Yearly susceptibility trend of X isolated from ...` (Enterobacterales;
  non-fermenters 2023/2024), `Yearly **susceptible** trend of ...`
  (non-fermenters, 2022 edition), and `**Year-wise** susceptibility **trends**
  of X from ...` (staphylococci, all editions).
- **Chapter renumbering again.** Non-fermenters sit in Chapter 5 (2022),
  Chapter 4 (2023) and Chapter 3 (2024). Staphylococci: Chapter 6, 7, 6.
- **Panels differ per organism, not just per chapter.** *A. baumannii* carries
  minocycline; *P. aeruginosa* carries gentamicin, tobramycin and
  ciprofloxacin. MRSA's panel omits cotrimoxazole and linezolid that *S.
  aureus* carries. Daptomycin appears only in specimen-wise tables, never in a
  yearly trend table.
- **Colistin is not a susceptibility figure.** Both non-fermenter tables
  footnote it: "*Colistin represents percentage intermediate susceptibility".
  Flagged `colistin_is_intermediate_susceptibility` on all 42 affected rows and
  excluded from the charts, where a ~97% colistin line beside a 9% meropenem
  line would read as "colistin still works".
- **Numbers wrap mid-digits.** The MRSA table's narrow columns split
  `4286/4311` into `4286/431` and a lone `1` on the next line — a denominator
  short by a digit, giving a susceptibility of 994%.
- **Year headers split across two rows.** Table 6.9 puts `Year-2020` on one
  header row and the other seven years as bare digits on the next.
- **Table 1.12b is an isolation trend, not a susceptibility trend** — excluded
  by requiring "susceptibility"/"susceptible" in the caption.

### Reconciling printed values

Three cells where a printed percentage and its own printed counts do not fully
reconcile. Carried as printed and flagged; not adjusted.

- ***P. aeruginosa* / piperacillin-tazobactam / 2022** is printed
  `9017/113156 (68.5)` in the 2022 **and** 2023 editions; that ratio would be
  7.97%. The 2024 edition prints `9017/13156` = 68.54%, matching the stated
  percentage — the later edition's denominator has one fewer digit and
  reconciles.
- ***A. baumannii* / minocycline / 2022**: all three editions print
  `6207/10542` (58.88%); the 2022 edition renders the percentage as 58.5 and
  the 2023 and 2024 editions as 58.8.

### Revised values found (V1.1)

17 revisions across 432 (organism, antibiotic, year) combinations covered by
two or more editions — 16 count revisions, 1 percentage revision. Beyond the
E. coli denominator change already logged for V1, one pattern recurs: for
**tigecycline, vancomycin and teicoplanin** in both *S. aureus* and MRSA,
earlier editions print a numerator equal to the denominator (a flat 100%) and a
later edition reports a lower numerator — e.g. *S. aureus* / tigecycline / 2022
is `2452/2452` (100%) in the 2022 edition but `2314/2452` (94.4%) in the 2023
and 2024 editions. Worth knowing before quoting any "100% effective" claim from
a single edition.

### Landing page
- **References section**, Vancouver style, generated by `src/references.py`
  from the same `sources.py` registry the fetcher uses, so the bibliography
  cannot drift from what the code actually downloaded. Includes the i-AMRSS
  methodology paper (doi:10.1093/jacamr/dlab023), which is what substantiates
  the note in the README and `DATA_LICENSE.md` that isolate-level data is not
  yet publicly released: "The data in the system are not yet publicly available."
- **Scope and maintenance note** on the page and in the README: data is current
  through the 8th edition (2024) and the repository is not maintained against
  future editions.
- **Interactive charts.** `index.html` now has two rendering paths: the static
  PNGs (no JavaScript required) and interactive inline-SVG charts that load
  `docs/data/trends.json`. Scroll-triggered reveal via `IntersectionObserver`,
  multi-select comparison by clicking legend entries, and a reset control.
- To stop the two paths diverging, `docs/data/trends.json` is emitted by the
  same `latest_edition_series()` used to draw the PNGs, with the same
  exclusions. 9 KB, against 599 KB for the full dataset.
- No charting library. The brief assumed Chart.js was already available; it was
  not, and the page had no scripts at all. Rather than add a CDN dependency or
  vendor a library, the charts are ~200 lines of vanilla JS emitting SVG.

### Fixed
- **The reveal animation could have blanked the entire page.** `.reveal` set
  `opacity: 0` unconditionally in CSS, so any JavaScript failure would have
  left every section invisible with no error. The hidden state is now scoped
  behind a class JavaScript adds, and a backstop drops the transition entirely
  after a short delay — observed while testing, where an
  `IntersectionObserver` in a non-compositing tab never fired and the page
  stayed blank. Readability must not depend on an animation completing.
- A fast-path filter in `find_caption` tested for the literal string
  `"usceptibility trend"` before running the caption regex, silently skipping
  every page of the 2022 non-fermenter chapter, whose captions read
  "susceptible trend". The tables matched the regex but never reached it. This
  was a bug in this repository, not in the PDFs, and is recorded because
  nothing about it was visible in the output — the two organisms simply
  reported "caption not found". Pre-filters must stay in step with the pattern
  they guard.

### Verified
- The 2022 source URL was re-fetched from ICMR, its SHA-256 confirmed to match
  the pinned value in `src/sources.py`, and its **contents** confirmed to be the
  AMRSN report (title page: "Antimicrobial Resistance Research and Surveillance
  Network, January 2022 to December 2022"; 223 ICMR mentions; contains the
  Tables 3.6/3.7 the parser reads) rather than trusting its filename.

---

## 0.1.0 — V1 (*E. coli*, *K. pneumoniae*)

### Added
- V1 pipeline: fetch → parse → validate → export for the Enterobacterales
  yearly susceptibility trend tables.
- Organisms: *Escherichia coli*, *Klebsiella pneumoniae*, 2017–2024, all
  samples except faeces and urine, 10-antibiotic panel.
- Report editions ingested: 2022 (6th), 2023 (7th), 2024 (8th).
- Cross-report revision detection (`data/processed/revisions.json`).
- Fixture validation against 28 values, including narrative-stated figures
  cross-checked against table-extracted ones. 64 tests in total.
- Trend charts, plus a chart of cross-edition differences.

### Source findings

These are properties of ICMR's published reports, recorded because they affect
how the data must be read.

- **Chapter renumbering, 2023 → 2024 edition.** Enterobacterales moved from
  Chapter 3 to Chapter 2. The *E. coli* yearly trend table is Table 3.6 in the
  2022 and 2023 editions but Table 2.6 in the 2024 edition; *K. pneumoniae* is
  Table 3.7 → Table 2.7. Tables are therefore located by caption text, never by
  number or page.
- **Organism name spelling, 2022 edition.** Table 3.7 is captioned "Klebsiella
  pneumonia" (without the trailing *e*). Organism matching tolerates this.
- **Near-duplicate captions.** Each edition also carries a urine-only trend
  table with an almost identical caption. V1 uses the "all samples (except
  faeces and urine)" tables and explicitly rejects the urine ones.
- **Text layer is not tabular.** `pdftotext -layout` output does not preserve
  row/column alignment for these tables — labels detach from their rows and
  later year columns are vertically offset. Extraction uses pdfplumber ruling
  lines only; the parser raises rather than falling back to text regex.
- **Header and data cells are offset by one column, 2023 edition.** The header
  row carries an extra leading cell, so `Year-2017` sits at column index 4
  while its data sits at index 3. Cells are matched to years by x-coordinate,
  not by index.
- **Ruled cells are narrower than their contents, 2022 edition.** The final
  year column clips overhanging digits: `5170 / 14729` extracts as
  `170 / 1472`, `9980 / 14304` as `980 / 1430`. The printed percentage is
  unaffected, so the corruption is invisible without an arithmetic check. Cell
  contents are assembled from whole words positioned by centre point.
- **Merged label cells produce nested phantom rows.** The wrapped
  "Piperacillin- / tazobactam" label yields a sub-row inside the real data row
  that repeats its percentage; unfiltered, it is absorbed by cefazolin and
  overwrites cefazolin's percentage with 56.8%.
- **Zero-denominator cells exist.** *K. pneumoniae* / cefazolin / 2018 is
  printed `*0/0 (-)` — no isolates tested that year. Flagged
  `no_isolates_tested`; no percentage is derived.

### Data-integrity decisions

- **Suppressed percentages are not reconstructed.** Where the source shows `(-)`
  in place of a percentage (cells such as `*0/8`), `susceptible_pct` is left
  null. The counts are still published, and `computed_pct` still carries n/N,
  labelled as derived. Publishing `0.0%` for `0/8` would introduce a figure the
  source itself does not report. 34 of 420 rows are affected.
- **Rounding is not reported as revision.** Differences that arise purely from
  printing precision (2023 prints `14.94%`, 2024 prints `14.9%`, both from
  `1021/6833`) are excluded from `revisions.json`. Six of the seven raw
  cross-edition differences in V1 are of this kind.
- **Low-count points are omitted from charts** (fewer than 30 isolates tested,
  or asterisked by ICMR). Presentational only — the rows stay in the dataset.

### Revised values found

One genuine revision across 140 (organism, antibiotic, year) combinations
covered by two or more editions:

- ***E. coli*, piperacillin-tazobactam, 2022** — denominator revised from
  **14729** (2022 and 2023 editions) to **14728** (2024 edition); numerator
  unchanged at 5170. The printed percentage is 35.1% in all three, so this is
  invisible to any comparison based on percentages alone.

### Corrections to the build spec

- **Spec section 4 fixture.** *E. coli* / meropenem / 2024 was listed as
  `62.9% (7594/12061)` with the numerator marked uncertain. The 2024 edition,
  Table 2.6, prints **7587/12061** = 62.90%. (7594/12061 rounds to 63.0%.) The
  verified value is now the fixture.
- **Spec section 3 schema example.** The illustrative row gave *K. pneumoniae* /
  meropenem / 2024 as `4283/12189`. Table 2.7 of the 2024 edition prints
  **4276/12189**. Both round to 35.1%, so this was invisible at the printed
  precision. (The spec presented this as an illustrative schema example rather
  than a verified figure.)
- **Spec sections 2 and 8 (V4).** Pre-2022 editions were assumed to be reachable
  only via Joomla flipbook viewers requiring reverse-engineering. At least the
  2019 and 2021 editions are in fact served as plain PDFs from the same
  `custom_data/pdf/resource-guidelines/` directory as the 2022 edition. URLs
  recorded in `src/sources.py` as `KNOWN_ARCHIVE_URLS` (unfetched, unverified).
- **Spec section 2, 2022/2023 URLs.** Resolved and pinned with SHA-256 in
  `src/sources.py`. The 2023 edition is served from `uploads/Documents/` under
  the generic filename `1725536060_annual_report_2023.pdf`, which does not
  follow the `icmramrsnannualreport<year>.pdf` pattern of the 2024 edition;
  it was confirmed to be the AMRSN report by inspecting its contents, not its
  filename.

