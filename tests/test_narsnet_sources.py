"""V3 -- the NARS-Net source registry, and the guarantee that V1/V2 did not move.

These tests are pure data checks over `src/sources.py`; nothing here touches the
network or the disk.

Two of them carry most of the weight:

* `test_hashes_match_the_investigation_record` re-reads the eight SHA-256 values
  out of `docs/narsnet_investigation_artifacts.md` and compares them against the
  registry. Every table location, caption and known source defect recorded in
  `docs/narsnet_v3_research.md` was established against exactly those bytes, so a
  transcription slip in the registry would silently point V3 at a document the
  research does not describe.

* `test_amrsn_registry_is_unchanged` pins the AMRSN registry against the V3
  edits. Adding a second registry and two optional dataclass fields must leave
  the V1/V2 fetch path byte-identical in behaviour, and asserting that is
  cheaper than discovering otherwise later.
"""

from __future__ import annotations

import re

import pytest

from src import fetch
from src.sources import (
    NARSNET_SOURCES,
    RAW_DIR,
    REGISTRIES,
    REPO_ROOT,
    SOURCES,
)

NARSNET_YEARS = list(range(2017, 2025))

# The two editions whose cover-page year is not their reporting period.
EXPECTED_COVER_YEARS = {2019: 2020, 2020: 2021}

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


# --- the NARS-Net registry --------------------------------------------------


def test_eight_editions_keyed_by_reporting_period():
    assert sorted(NARSNET_SOURCES) == NARSNET_YEARS
    for year, src in NARSNET_SOURCES.items():
        assert src.report_year == year
        assert src.network == "narsnet"
        assert src.verified_on == "2026-09-01"


def test_urls_are_the_legacy_uploads_pdf_paths():
    """The `/wp-content/` copies also resolve, but the 2024 one truncates before
    Annexure I. `docs/narsnet_v3_research.md` A3 settles on these paths."""
    for src in NARSNET_SOURCES.values():
        assert src.url.startswith("https://ncdc.mohfw.gov.in/uploads/pdf/amr")
        assert src.url.endswith(".pdf")

    urls = [s.url for s in NARSNET_SOURCES.values()]
    assert len(set(urls)) == len(urls), "an NCDC URL is repeated across editions"


def test_hashes_are_pinned_and_distinct():
    digests = [s.sha256 for s in NARSNET_SOURCES.values()]
    assert all(d is not None for d in digests), "every NARS-Net source must be pinned"
    assert all(SHA256_RE.match(d) for d in digests)
    assert len(set(digests)) == len(digests), "two editions share a hash"


def test_hashes_match_the_investigation_record():
    """The registry must agree with `docs/narsnet_investigation_artifacts.md`."""
    doc = (REPO_ROOT / "docs" / "narsnet_investigation_artifacts.md").read_text(
        encoding="utf-8"
    )
    row = re.compile(
        r"\|\s*Jan.Dec\s+(?P<year>\d{4})\s*\|"
        r"\s*`(?P<filename>[^`]+)`\s*\|"
        r"\s*(?P<url>https?://\S+)\s*\|"
        r"\s*`(?P<sha>[0-9a-f]{64})`\s*\|"
    )
    recorded = {
        int(m.group("year")): (
            m.group("filename"),
            m.group("url"),
            m.group("sha"),
        )
        for m in row.finditer(doc)
    }

    assert sorted(recorded) == NARSNET_YEARS, (
        "could not read all eight rows out of the investigation record; "
        "found {}".format(sorted(recorded))
    )
    for year, (filename, url, sha) in recorded.items():
        src = NARSNET_SOURCES[year]
        assert src.filename == filename
        assert src.url == url
        assert src.sha256 == sha


def test_filenames_are_distinct_from_the_amrsn_ones():
    names = [s.filename for s in NARSNET_SOURCES.values()]
    assert len(set(names)) == len(names)
    assert not set(names) & {s.filename for s in SOURCES.values()}
    for year, src in NARSNET_SOURCES.items():
        assert src.filename == "narsnet_{}.pdf".format(year)
        assert src.path.parent == RAW_DIR


def test_cover_years_are_recorded_only_where_they_differ():
    """The 2019-data edition's cover reads "-2020" and the 2020-data edition's
    reads "-2021". Nothing is keyed on a cover year, but the discrepancy is
    carried rather than resolved silently."""
    for year, src in NARSNET_SOURCES.items():
        assert src.cover_year == EXPECTED_COVER_YEARS.get(year)


def test_edition_records_the_reporting_period():
    """NARS-Net editions carry no ordinal, no ISBN and no DOI (research A7)."""
    for year, src in NARSNET_SOURCES.items():
        assert src.edition == "Jan-Dec {}".format(year)


# --- V1/V2 must not have moved ----------------------------------------------


def test_amrsn_registry_is_unchanged():
    assert sorted(SOURCES) == [2022, 2023, 2024]
    assert {y: s.edition for y, s in SOURCES.items()} == {
        2022: "6th",
        2023: "7th",
        2024: "8th",
    }
    assert {y: s.sha256 for y, s in SOURCES.items()} == {
        2022: "cf669d2a8193cdd28987f1e88b983c4474fbeb2ead08ca9352f831f39b272482",
        2023: "09c5afde7a7d1401d275993f60e97ae4b5f12630ba29497331429fa09430dbdc",
        2024: "9a078ba24e7dc052a1bf4b0f623ab5ea3e5bad8d4787c584d96008b55d24d852",
    }
    for src in SOURCES.values():
        assert src.filename == "amrsn_{}.pdf".format(src.report_year)
        assert src.url.startswith("https://www.icmr.gov.in/")
        # The two fields V3 added default to the V1 meaning.
        assert src.network == "amrsn"
        assert src.cover_year is None


# --- registry wiring and fetch policy ---------------------------------------


def test_registries_expose_exactly_the_two_networks():
    assert REGISTRIES == {"amrsn": SOURCES, "narsnet": NARSNET_SOURCES}


def test_only_narsnet_is_strict_about_a_changed_hash():
    """A re-upload invalidates the recorded V3 investigation, not just the
    download, so it fails the fetch instead of warning and proceeding."""
    assert fetch.STRICT_HASH_NETWORKS == {"narsnet"}
    for src in NARSNET_SOURCES.values():
        assert src.network in fetch.STRICT_HASH_NETWORKS
    for src in SOURCES.values():
        assert src.network not in fetch.STRICT_HASH_NETWORKS


def test_fetch_defaults_to_the_amrsn_registry():
    """Both registries are keyed by year, so `--year` alone must still mean
    AMRSN. 2019 is a NARS-Net edition and not an AMRSN one, which makes it the
    year that tells the two defaults apart -- no network access needed."""
    with pytest.raises(SystemExit):
        fetch.main(["--year", "2019"])


def test_unknown_year_is_rejected_per_selected_network():
    with pytest.raises(SystemExit):
        fetch.main(["--network", "narsnet", "--year", "2016"])
    with pytest.raises(SystemExit):
        fetch.main(["--network", "all", "--year", "2016"])
