# Data License & Attribution

This file governs the **data** in `data/processed/`. The **code** in this repository is
licensed separately under the MIT License (see `LICENSE`).

## Source material (not licensed by this project)

The underlying source documents are the ICMR AMRSN annual reports, which carry an
explicit copyright notice:

> © Indian Council of Medical Research, New Delhi. All rights reserved.

This project claims **no rights whatsoever** over those reports.

- The source PDFs are **not redistributed** by this repository. They are downloaded to
  `data/raw/`, which is gitignored. `src/fetch.py` retrieves them at run time from
  ICMR's own public URLs.
- No report text, layout, figures, or table images are reproduced here.

## What this project does claim

`data/processed/` contains **individual factual measurements** (numerator, denominator,
percentage) extracted from published tables and restructured into a normalised,
machine-readable schema of this project's own design (one row per
organism × antibiotic × year × source report).

Individual facts are not copyrightable. The selection, normalisation, schema design,
cross-report reconciliation logic, and provenance annotation are this project's original
contribution, and are released under
**Creative Commons Attribution 4.0 International (CC BY 4.0)**.

This is a deliberately conservative position: extract the numbers, cite them precisely,
reproduce nothing.

## Required attribution

Any use of the processed dataset must cite **both**:

1. **The original source** — ICMR AMRSN, the specific report year, and the specific
   table number. Every row in the dataset carries `source_report_year`, `source_table`,
   and `source_url` for exactly this purpose.
2. **This project** — see `CITATION.cff`.

## Disclaimer

> Derived from publicly available ICMR AMRSN annual reports (2017–2024).
> Independent, unofficial analysis — not endorsed by or affiliated with ICMR.

This dataset is **not** a substitute for the official reports. Where this dataset and an
ICMR report disagree, **the report is correct and this dataset has a bug** — please open
an issue.

## What this data is NOT

- Not community prevalence — these are hospital laboratory isolates from tertiary-care
  centres, a heavily selected population.
- Not patient-level data. ICMR does not release isolate-level records publicly.
- Not a national incidence or burden estimate.
- Not comparable to NCDC NARS-Net figures without explicit labelling — that is a
  different surveillance network with a different site panel.
