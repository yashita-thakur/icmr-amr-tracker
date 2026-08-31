# Changelog

Every ingested report edition and every revised value found is logged here
(spec section 5).

## [Unreleased] — 0.3.0 (V2 — Regional Centre breakdowns)

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

