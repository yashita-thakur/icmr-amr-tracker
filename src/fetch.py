"""Download annual report PDFs into data/raw/ (spec §4.1).

data/raw/ is gitignored. Per spec §7 these PDFs are never redistributed by this
repository -- every user fetches them from the publisher directly.

Two registries are served, selected with --network: ICMR AMRSN (V1/V2) and NCDC
NARS-Net (V3). The default is the AMRSN registry, so every invocation that
worked before V3 still means exactly what it did.

Usage:
    python -m src.fetch                       # fetch all AMRSN reports
    python -m src.fetch --year 2024           # fetch one
    python -m src.fetch --network narsnet     # fetch all 8 NARS-Net editions
    python -m src.fetch --network all         # both registries
    python -m src.fetch --verify-only         # re-check hashes of what is on disk
"""

from __future__ import annotations

import argparse
import hashlib
import sys

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests

from .sources import RAW_DIR, REGISTRIES, ReportSource

# icmr.gov.in rejects requests without a browser-like UA and does not support HEAD.
# ncdc.mohfw.gov.in serves its PDFs without either requirement, so one header set
# covers both publishers.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
TIMEOUT = 300

# Networks whose pinned hashes are a precondition rather than a nicety. Every
# table location, caption and known source defect recorded in
# `docs/narsnet_v3_research.md` was established against specific bytes; if the
# file at a URL has changed, that investigation no longer describes the document
# and extraction must stop until it is re-verified. So a mismatch here fails the
# fetch instead of warning and proceeding. Keyed by network, never by hostname --
# this says how much a registry's recorded findings depend on the exact file, not
# who serves it.
STRICT_HASH_NETWORKS = {"narsnet"}


def sha256_of(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_one(
    src: ReportSource, force: bool = False, strict: bool | None = None
) -> bool:
    """Download one report. Returns True if the file on disk is trustworthy.

    `strict` decides what a changed hash means on a fresh download. Left as None
    it follows STRICT_HASH_NETWORKS for the source's own network.
    """
    if strict is None:
        strict = src.network in STRICT_HASH_NETWORKS
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

    # Content-Type is advisory. A publisher may serve a perfectly good PDF as
    # application/octet-stream, and refusing on that alone would reject it. The
    # magic-byte check below is the real gate.
    ctype = resp.headers.get("Content-Type", "")
    if "pdf" not in ctype.lower():
        print(
            f"  [note]     {src.filename}: Content-Type {ctype!r} is not a PDF "
            f"type. Continuing; the %PDF- check below decides."
        )

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
        if strict:
            tmp.unlink()
            print(
                f"  [REJECTED] {src.filename} downloaded OK but its hash "
                f"has CHANGED.\n"
                f"             Pinned  {src.sha256} (verified {src.verified_on})\n"
                f"             Now     {digest}\n"
                f"             The publisher has re-uploaded this report. For"
                f" the {src.network} registry the pinned hash is a\n"
                f"             precondition: the recorded table locations and"
                f" known source defects were\n"
                f"             established against the pinned bytes and may not"
                f" describe this file.\n"
                f"             Not written to disk. Re-verify the source against"
                f" docs/, then update\n"
                f"             the pin and log the change in CHANGELOG.md."
            )
            return False
        print(
            f"  [WARNING]  {src.filename} downloaded OK but its hash has CHANGED.\n"
            f"             Pinned  {src.sha256} (verified {src.verified_on})\n"
            f"             Now     {digest}\n"
            f"             The publisher appears to have re-uploaded this"
            f" report. Any numbers\n"
            f"             extracted from it may differ from previously"
            f" published results.\n"
            f"             Investigate before trusting the output, and log the"
            f" change in CHANGELOG.md."
        )

    tmp.replace(src.path)
    size_mb = src.path.stat().st_size / 1e6
    print(f"  [ok]       {src.filename} ({size_mb:.1f} MB, sha256 {digest[:16]}...)")
    return True


def verify_all(registry) -> bool:
    ok = True
    for year in sorted(registry, reverse=True):
        src = registry[year]
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
    ap.add_argument(
        "--network",
        choices=(*sorted(REGISTRIES), "all"),
        default="amrsn",
        help="which registry to act on (default: amrsn)",
    )
    ap.add_argument("--year", type=int, action="append", help="report year (repeatable)")
    ap.add_argument("--force", action="store_true", help="re-download even if cached")
    ap.add_argument("--verify-only", action="store_true", help="only check hashes")
    args = ap.parse_args(argv)

    networks = sorted(REGISTRIES) if args.network == "all" else [args.network]

    if args.verify_only:
        ok = True
        for network in networks:
            print(f"Verifying {network} sources in data/raw/ against pinned hashes:")
            ok &= verify_all(REGISTRIES[network])
        return 0 if ok else 1

    # Both registries are keyed by year and both cover 2022-2024, so a --year is
    # only unknown if no *selected* registry has it.
    if args.year:
        known = sorted({y for n in networks for y in REGISTRIES[n]})
        unknown = [y for y in args.year if y not in known]
        if unknown:
            ap.error(f"unknown report year(s): {unknown}; known: {known}")

    ok = True
    for network in networks:
        registry = REGISTRIES[network]
        years = (
            [y for y in args.year if y in registry]
            if args.year
            else sorted(registry, reverse=True)
        )
        if not years:
            continue
        print(f"Fetching {len(years)} {network} report(s) into {RAW_DIR}")
        for year in years:
            try:
                ok &= fetch_one(registry[year], force=args.force)
            except Exception as exc:  # noqa: BLE001 - report and continue
                print(f"  [FAILED]   {registry[year].filename}: {exc}")
                ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
