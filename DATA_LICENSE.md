# Data License & Attribution

This file governs the **data** in `data/processed/`. The **code** in this repository is
licensed separately under the MIT License (see `LICENSE`).

## Source material (not licensed by this project)

The underlying source documents are the annual reports of two Indian national AMR
surveillance networks, and their front matter differs:

- **ICMR-AMRSN** reports carry an explicit copyright notice:

  > © Indian Council of Medical Research, New Delhi. All rights reserved.

- **NCDC NARS-Net** reports carry no copyright notice, ISBN or DOI that this project
  has been able to find. Absence of a notice is not a grant of rights, so the same
  conservative position is taken for both.

This project claims **no rights whatsoever** over either body's reports.

- The source PDFs are **not redistributed** by this repository. They are downloaded to
  `data/raw/`, which is gitignored. `src/fetch.py` retrieves them at run time from
  ICMR's and NCDC's own public URLs.
- No report text, layout, figures, or table images are reproduced here.

## What this project does claim

`data/processed/` contains **individual factual measurements** (numerator, denominator,
percentage) extracted from published tables and restructured into normalised,
machine-readable schemas of this project's own design. The two networks have
**separate schemas in separate files**, because they do not describe the same
quantity: `amr_trends.csv` is one row per organism × antibiotic × year × source
report, carrying AMRSN's **% susceptible**; `narsnet_trends.csv` is one row per
organism × antibiotic × specimen × edition, carrying NARS-Net's **% resistant**.

Individual facts are not copyrightable. The selection, normalisation, schema design,
cross-report reconciliation logic, and provenance annotation are this project's original
contribution, and are released under
**Creative Commons Attribution 4.0 International (CC BY 4.0)**.

This is a deliberately conservative position: extract the numbers, cite them precisely,
reproduce nothing.

## Required attribution

Any use of the processed dataset must cite **both**:

1. **The original source** — the network the row came from (ICMR-AMRSN or NCDC
   NARS-Net), the specific report year, and the specific table number. Every row in
   both datasets carries `source_report_year`, `source_table`, and `source_url` for
   exactly this purpose, and NARS-Net rows additionally carry `network` and the
   `source_cover_year` where an edition's cover year is not its reporting period.
2. **This project** — see `CITATION.cff`.

## Disclaimer

> Derived from the publicly available annual reports of two independent Indian national
> AMR surveillance networks: ICMR-AMRSN (2017–2024) and NCDC NARS-Net (2019–2020). The
> two are published here as parallel series and are never pooled. Independent,
> unofficial analysis — not endorsed by or affiliated with ICMR or NCDC.

These datasets are **not** a substitute for the official reports. Where a dataset and the
corresponding published report differ, **the published report is authoritative and the
difference is a limitation of this extraction** — please open an issue.

## What this data is NOT

- Not community prevalence — these are hospital laboratory isolates from tertiary-care
  centres, a heavily selected population.
- Not patient-level data. Isolate-level records are not part of the public release.
- Not a national incidence or burden estimate.
- Not a single pooled series across the two networks. AMRSN and NARS-Net recruit from
  different institutional strata and publish different metrics — % susceptible and
  % resistant respectively — and AMRSN publishes no % intermediate for *E. coli* or
  *S. aureus*, so the two cannot be converted onto a shared value. They are kept in
  separate files and must be read as parallel series, each labelled with its network.
