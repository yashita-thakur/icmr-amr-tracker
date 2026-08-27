"""Registry of ICMR AMRSN annual report PDFs.

Spec §7: these PDFs are copyrighted by ICMR and are NEVER committed to this repo.
This module records only *where they live* and *what they should hash to*, so that
any third party can fetch byte-identical inputs and reproduce our numbers.

The `sha256` values were recorded on the date in `verified_on`. ICMR occasionally
re-uploads a report at the same URL; a hash mismatch is therefore a meaningful
event (the source document changed), not merely a broken download. See
`fetch.py`, which surfaces this rather than silently overwriting.
"""

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"


@dataclass(frozen=True)
class ReportSource:
    """One ICMR AMRSN annual report edition."""

    report_year: int
    edition: str
    url: str
    filename: str
    sha256: str | None
    verified_on: str

    @property
    def path(self) -> Path:
        return RAW_DIR / self.filename


# --- V1 scope (spec §2.1): the three most recent editions -------------------
# Each of these contains an 8-year retrospective trend table, so three PDFs are
# enough to cover 2017-2024 three times over -- which is what makes cross-report
# revision detection possible at all.
SOURCES: dict[int, ReportSource] = {
    2024: ReportSource(
        report_year=2024,
        edition="8th",
        url=(
            "https://www.icmr.gov.in/icmrobject/uploads/Report/"
            "1763981012_icmramrsnannualreport2024.pdf"
        ),
        filename="amrsn_2024.pdf",
        sha256="9a078ba24e7dc052a1bf4b0f623ab5ea3e5bad8d4787c584d96008b55d24d852",
        verified_on="2026-08-25",
    ),
    2023: ReportSource(
        report_year=2023,
        edition="7th",
        url=(
            "https://www.icmr.gov.in/icmrobject/uploads/Documents/"
            "1725536060_annual_report_2023.pdf"
        ),
        filename="amrsn_2023.pdf",
        sha256="09c5afde7a7d1401d275993f60e97ae4b5f12630ba29497331429fa09430dbdc",
        verified_on="2026-08-25",
    ),
    2022: ReportSource(
        report_year=2022,
        edition="6th",
        url=(
            "https://www.icmr.gov.in/icmrobject/custom_data/pdf/resource-guidelines/"
            "AMRSN_Annual_Report_2022.pdf"
        ),
        filename="amrsn_2022.pdf",
        sha256="cf669d2a8193cdd28987f1e88b983c4474fbeb2ead08ca9352f831f39b272482",
        verified_on="2026-08-25",
    ),
}

# --- Out of V1 scope, but resolved and kept here so V4 need not re-research --
# Spec §2/§8 assumed pre-2022 editions were reachable only through Joomla
# "flipbook" viewers requiring reverse-engineering. That is not the case: at
# least the 2019 and 2021 editions are served as plain PDFs from the same
# `custom_data/pdf/resource-guidelines/` directory as the 2022 edition.
# Hashes are deliberately None -- these have not been fetched or verified.
KNOWN_ARCHIVE_URLS: dict[int, str] = {
    2021: (
        "https://www.icmr.gov.in/icmrobject/custom_data/pdf/resource-guidelines/"
        "AMR_Annual_Report_2021.pdf"
    ),
    2019: (
        "https://www.icmr.gov.in/icmrobject/custom_data/pdf/resource-guidelines/"
        "Final_AMRSN_Annual_Report_2019_29072020.pdf"
    ),
}

ATTRIBUTION = (
    "Derived from publicly available ICMR AMRSN annual reports (2017-2024). "
    "Independent, unofficial analysis - not endorsed by or affiliated with ICMR."
)
