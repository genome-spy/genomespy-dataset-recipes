#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0

# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""Prepare and validate the pinned GIAB HG002 BAM slice."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

RECIPE_DIR = Path(__file__).resolve().parents[1]
DOWNLOAD_DIR = RECIPE_DIR / "download"
OUTPUT_DIR = RECIPE_DIR / "output"
PROVENANCE_PATH = RECIPE_DIR / "provenance.json"
REGION = "chr20:9950000-10100000"
EXPECTED_RECORDS = 101_867
EXPECTED_MAPPED = 101_159
USER_AGENT = "GenomeSpy dataset recipe nist-hg002-grch38-bam-slice"


def digest(path: Path, algorithm: str) -> str:
    """Return a hexadecimal file digest."""

    value = hashlib.new(algorithm)
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def download(url: str, destination: Path, expected: str, algorithm: str) -> None:
    """Download a pinned file atomically and verify it."""

    if destination.exists() and digest(destination, algorithm) == expected:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request) as response, temporary.open("wb") as output:
        shutil.copyfileobj(response, output)
    if digest(temporary, algorithm) != expected:
        temporary.unlink()
        raise ValueError(f"Checksum mismatch for {url}")
    temporary.replace(destination)


def run(*arguments: str, capture: bool = False) -> str:
    """Run samtools and return standard output when requested."""

    result = subprocess.run(
        ["samtools", *arguments],
        check=True,
        capture_output=capture,
        text=capture,
    )
    return result.stdout if capture else ""


def validate(bam: Path, bai: Path) -> dict[str, int]:
    """Validate the BAM/BAI pair and return stable semantic counts."""

    if not bam.is_file() or not bai.is_file():
        raise FileNotFoundError("Both output/alignments.bam and its BAI are required")
    run("quickcheck", str(bam))
    record_count = int(run("view", "-c", str(bam), capture=True).strip())
    mapped_count = int(run("view", "-c", "-F", "4", str(bam), capture=True).strip())
    indexed_count = int(run("view", "-c", str(bam), REGION, capture=True).strip())
    if record_count != EXPECTED_RECORDS or indexed_count != EXPECTED_RECORDS:
        raise ValueError(f"Expected {EXPECTED_RECORDS} records, found {record_count}")
    if mapped_count != EXPECTED_MAPPED:
        raise ValueError(
            f"Expected {EXPECTED_MAPPED} mapped records, found {mapped_count}"
        )
    return {"records": record_count, "mapped": mapped_count}


def verify_accepted_outputs() -> None:
    """Compare existing artifacts with the accepted provenance record."""

    provenance: dict[str, Any] = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    bam = OUTPUT_DIR / "alignments.bam"
    bai = OUTPUT_DIR / "alignments.bam.bai"
    validate(bam, bai)
    for key, path in (("bam", bam), ("bai", bai)):
        expected = provenance["outputs"][key]
        if path.stat().st_size != expected["fileSizeBytes"]:
            raise ValueError(f"Size mismatch for {path.name}")
        if digest(path, "sha256") != expected["sha256"]:
            raise ValueError(f"SHA-256 mismatch for {path.name}")
    print("Accepted BAM and BAI match provenance and semantic checks.")


def prepare() -> None:
    """Create the pinned regional subsample from the remote parent BAM."""

    provenance: dict[str, Any] = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    source = provenance["sources"][0]
    index = source["sourceIndex"]
    download(
        index["url"],
        DOWNLOAD_DIR / "giab-alignment-index.txt",
        index["sha256"],
        "sha256",
    )
    parent_bai = DOWNLOAD_DIR / "parent.bam.bai"
    download(
        source["baiUrl"],
        parent_bai,
        source["baiMd5"],
        "md5",
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    bam = OUTPUT_DIR / "alignments.bam"
    temporary = OUTPUT_DIR / "alignments.bam.part"
    run(
        "view",
        "--no-PG",
        "-b",
        "-s",
        "42.33",
        "-X",
        "-o",
        str(temporary),
        source["bamUrl"],
        str(parent_bai),
        REGION,
    )
    temporary.replace(bam)
    run("index", "-o", str(OUTPUT_DIR / "alignments.bam.bai"), str(bam))
    counts = validate(bam, OUTPUT_DIR / "alignments.bam.bai")
    print(f"Prepared {counts['records']} records ({counts['mapped']} mapped).")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Validate existing outputs against committed provenance",
    )
    return parser.parse_args()


def main() -> None:
    """Prepare or verify the recipe output."""

    arguments = parse_args()
    if arguments.verify_only:
        verify_accepted_outputs()
    else:
        prepare()


if __name__ == "__main__":
    main()
