"""Download ICMR AMRSN annual report PDFs into data/raw/ (spec §4.1).

data/raw/ is gitignored. Per spec §7 these PDFs are never redistributed by this
repository -- every user fetches them from ICMR directly.

Usage:
    python -m src.fetch                 # fetch all V1 reports
    python -m src.fetch --year 2024     # fetch one
    python -m src.fetch --verify-only   # re-check hashes of what is on disk
"""

from __future__ import annotations

import argparse
import hashlib
import sys

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests

from .sources import RAW_DIR, SOURCES, ReportSource

# icmr.gov.in rejects requests without a browser-like UA and does not support HEAD.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
TIMEOUT = 300


def sha256_of(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_one(src: ReportSource, force: bool = False) -> bool:
    """Download one report. Returns True if the file on disk is trustworthy."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if src.path.exists() and not force:
        digest = sha256_of(src.path)
        if src.sha256 is None or digest == src.sha256:
            print(f"  [cached]   {src.filename}")
            return True
        print(
            f"  [MISMATCH] {src.filename} already on disk but hash differs from the\n"
            f"             pinned value. Expected {src.sha256}\n"
            f"             Got      {digest}\n"
            f"             Not overwriting. Re-run with --force to replace it."
        )
        return False

    print(f"  [fetching] {src.filename} <- {src.url}")
    resp = requests.get(src.url, headers=HEADERS, timeout=TIMEOUT, stream=True)
    resp.raise_for_status()

    ctype = resp.headers.get("Content-Type", "")
    if "pdf" not in ctype.lower():
        raise RuntimeError(f"{src.url} returned Content-Type {ctype!r}, expected PDF")

    tmp = src.path.with_suffix(".part")
    with open(tmp, "wb") as fh:
        for chunk in resp.iter_content(1 << 20):
            fh.write(chunk)

    with open(tmp, "rb") as fh:
        if fh.read(5) != b"%PDF-":
            tmp.unlink()
            raise RuntimeError(f"{src.url} did not return a PDF (bad magic bytes)")

    digest = sha256_of(tmp)
    if src.sha256 and digest != src.sha256:
        print(
            f"  [WARNING]  {src.filename} downloaded OK but its hash has CHANGED.\n"
            f"             Pinned  {src.sha256} (verified {src.verified_on})\n"
            f"             Now     {digest}\n"
            f"             ICMR appears to have re-uploaded this report. Any numbers\n"
            f"             extracted from it may differ from previously published\n"
            f"             results. Investigate before trusting the output, and log\n"
            f"             the change in CHANGELOG.md."
        )

    tmp.replace(src.path)
    size_mb = src.path.stat().st_size / 1e6
    print(f"  [ok]       {src.filename} ({size_mb:.1f} MB, sha256 {digest[:16]}...)")
    return True


def verify_all() -> bool:
    ok = True
    for year in sorted(SOURCES, reverse=True):
        src = SOURCES[year]
        if not src.path.exists():
            print(f"  [missing]  {src.filename}")
            ok = False
            continue
        digest = sha256_of(src.path)
        if src.sha256 and digest != src.sha256:
            print(f"  [MISMATCH] {src.filename}: {digest}")
            ok = False
        else:
            print(f"  [ok]       {src.filename}")
    return ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", type=int, action="append", help="report year (repeatable)")
    ap.add_argument("--force", action="store_true", help="re-download even if cached")
    ap.add_argument("--verify-only", action="store_true", help="only check hashes")
    args = ap.parse_args(argv)

    if args.verify_only:
        print("Verifying data/raw/ against pinned hashes:")
        return 0 if verify_all() else 1

    years = args.year or sorted(SOURCES, reverse=True)
    unknown = [y for y in years if y not in SOURCES]
    if unknown:
        ap.error(f"unknown report year(s): {unknown}; known: {sorted(SOURCES)}")

    print(f"Fetching {len(years)} ICMR AMRSN report(s) into {RAW_DIR}")
    ok = True
    for year in years:
        try:
            ok &= fetch_one(SOURCES[year], force=args.force)
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"  [FAILED]   {SOURCES[year].filename}: {exc}")
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
