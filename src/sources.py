"""Registry of the annual report PDFs this project extracts from.

Two networks, two registries, deliberately not merged:

* `SOURCES`         -- ICMR AMRSN editions (V1/V2).
* `NARSNET_SOURCES` -- NCDC NARS-Net editions (V3).

They cannot share one dict in any case: both are keyed by year and both cover
2022-2024. Keeping them apart also keeps the two networks' rows from ever being
addressed as one series, which is the standing constraint on V3 -- see the
metric mismatch note on `NARSNET_SOURCES`.

Spec §7: no source PDF of either network is committed to this repo. This module
records only *where they live* and *what they should hash to*, so that any third
party can fetch byte-identical inputs and reproduce our numbers.

The `sha256` values were recorded on the date in `verified_on`. Both publishers
occasionally re-upload a report at the same URL; a hash mismatch is therefore a
meaningful event (the source document changed), not merely a broken download.
See `fetch.py`, which surfaces this rather than silently overwriting.
"""

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"


@dataclass(frozen=True)
class ReportSource:
    """One annual report edition, from either surveillance network.

    `report_year` is the REPORTING PERIOD the edition covers, never the year
    printed on its cover. The two differ for NARS-Net: the edition reporting
    January-December 2019 has a cover reading "AMR Annual report -2020", and the
    2020-data edition's cover reads "Annual Report-2021". Where a cover year
    differs from the reporting period it is recorded in `cover_year`, so the
    discrepancy is carried in the data rather than resolved silently.

    `edition` holds an ordinal ("8th") where the publisher assigns one. NARS-Net
    editions carry no ordinal, no ISBN and no DOI, so for those it records the
    reporting period instead.
    """

    report_year: int
    edition: str
    url: str
    filename: str
    sha256: str | None
    verified_on: str
    network: str = "amrsn"
    cover_year: int | None = None

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

# --- V3 scope: NCDC NARS-Net ------------------------------------------------
# A second, independent Indian national AMR surveillance network, run by NCDC
# and separate from ICMR's AMRSN. Eight editions, one reporting period each.
#
# Read `docs/narsnet_v3_research.md` before using these. Three things about the
# series constrain every downstream decision:
#
# * NARS-Net publishes %RESISTANT; AMRSN publishes %SUSCEPTIBLE. Converting
#   between them needs the intermediate fraction, which AMRSN does not publish
#   for E. coli or S. aureus. The two networks can be presented as PARALLEL
#   SERIES only, and must never be joined on a single shared comparison value.
# * Cover-page years are unreliable (see `ReportSource`), so these are keyed and
#   cited by reporting period. `wp-content/uploads/2024/03/87909365291642417515.pdf`
#   is a duplicate of the 2020 edition, not a distinct year.
# * The `/uploads/pdf/amrNN.pdf` paths below are the ones to use. The
#   `/wp-content/` equivalents also resolve, but the 2024 copy there truncates
#   before Annexure I.
#
# The hashes were recorded during the V3 investigation on 2026-09-01, and every
# table location, caption and known source defect in `docs/narsnet_v3_research.md`
# was established against exactly these bytes. A mismatch therefore invalidates
# the investigation, not just the download, so `fetch.py` treats it as a hard
# failure for this registry rather than a warning.
NARSNET_SOURCES: dict[int, ReportSource] = {
    2024: ReportSource(
        report_year=2024,
        edition="Jan-Dec 2024",
        url="https://ncdc.mohfw.gov.in/uploads/pdf/amr30.pdf",
        filename="narsnet_2024.pdf",
        sha256="48b4bdf8f7f8706a110f9f8b3b95aa792b813b18ecedc7b1bb94b49c8a63c4e5",
        verified_on="2026-09-01",
        network="narsnet",
    ),
    2023: ReportSource(
        report_year=2023,
        edition="Jan-Dec 2023",
        url="https://ncdc.mohfw.gov.in/uploads/pdf/amr32.pdf",
        filename="narsnet_2023.pdf",
        sha256="1c5c9fbe3c6320c9b1e31852f0892aecf705d10c243fbb4505551b4032ebca56",
        verified_on="2026-09-01",
        network="narsnet",
    ),
    2022: ReportSource(
        report_year=2022,
        edition="Jan-Dec 2022",
        url="https://ncdc.mohfw.gov.in/uploads/pdf/amr34.pdf",
        filename="narsnet_2022.pdf",
        sha256="5d3734e4dbcc32fc4070e0b85ae0e164ff4fbcc90df4813ffc5c632a130867e7",
        verified_on="2026-09-01",
        network="narsnet",
    ),
    2021: ReportSource(
        report_year=2021,
        edition="Jan-Dec 2021",
        url="https://ncdc.mohfw.gov.in/uploads/pdf/amr35.pdf",
        filename="narsnet_2021.pdf",
        sha256="976a985af372cbd2f59a5afb7381a6a68edb0bcca33e95b98bc0b3deea306785",
        verified_on="2026-09-01",
        network="narsnet",
    ),
    # Cover reads "Annual Report-2021"; the reporting period is Jan-Dec 2020.
    2020: ReportSource(
        report_year=2020,
        edition="Jan-Dec 2020",
        url="https://ncdc.mohfw.gov.in/uploads/pdf/amr36.pdf",
        filename="narsnet_2020.pdf",
        sha256="159858e8674efc6ee4c800a34ef494ddc7d3e88a920f54e4c867a65aba2ec9ad",
        verified_on="2026-09-01",
        network="narsnet",
        cover_year=2021,
    ),
    # Cover reads "AMR Annual report -2020"; the reporting period is Jan-Dec 2019.
    2019: ReportSource(
        report_year=2019,
        edition="Jan-Dec 2019",
        url="https://ncdc.mohfw.gov.in/uploads/pdf/amr37.pdf",
        filename="narsnet_2019.pdf",
        sha256="6056c836ea739dd02cfc0af39295a49c41bffd4da31cfe302085b53a19fd3097",
        verified_on="2026-09-01",
        network="narsnet",
        cover_year=2020,
    ),
    2018: ReportSource(
        report_year=2018,
        edition="Jan-Dec 2018",
        url="https://ncdc.mohfw.gov.in/uploads/pdf/amr38.pdf",
        filename="narsnet_2018.pdf",
        sha256="a09987ec16fe77b10438cd3340bf1c2c4aae1cd330ba0601b33231453693836f",
        verified_on="2026-09-01",
        network="narsnet",
    ),
    2017: ReportSource(
        report_year=2017,
        edition="Jan-Dec 2017",
        url="https://ncdc.mohfw.gov.in/uploads/pdf/amr39.pdf",
        filename="narsnet_2017.pdf",
        sha256="0070d1b36c314a235bf1b744170e8e7bc95655db064c57cbb485f8301ffff6b2",
        verified_on="2026-09-01",
        network="narsnet",
    ),
}

# Every registry the fetcher knows about, by network key.
REGISTRIES: dict[str, dict[int, ReportSource]] = {
    "amrsn": SOURCES,
    "narsnet": NARSNET_SOURCES,
}

ATTRIBUTION = (
    "Derived from publicly available ICMR AMRSN annual reports (2017-2024). "
    "Independent, unofficial analysis - not endorsed by or affiliated with ICMR."
)
