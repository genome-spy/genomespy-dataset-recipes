#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Reconstruct the historical TAL1 reference bundle from UCSC hg38 DNA."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def verify(raw: bytes, record: dict[str, Any]) -> None:
    """Reject content that differs from the accepted identity."""
    if (
        len(raw) != record["fileSizeBytes"]
        or hashlib.sha256(raw).hexdigest() != record["sha256"]
    ):
        raise ValueError("Content differs from the pinned size or SHA-256")


def write_atomic(path: Path, raw: bytes) -> None:
    """Publish a complete, validated local file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(raw)
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def validate_sequence(sequence: str, metadata: dict[str, Any]) -> None:
    """Validate interval length, alphabet, digest, and control-base indexing."""
    interval = metadata["interval"]
    if len(sequence) != interval["end0"] - interval["start0"] or set(sequence) - set(
        "ACGT"
    ):
        raise ValueError("Invalid TAL1 sequence length or alphabet")
    if hashlib.sha256(sequence.encode()).hexdigest() != metadata["sequence_sha256"]:
        raise ValueError("TAL1 sequence differs from historical reference")
    control = metadata["positive_control_site"]
    offset = control["pos1"] - 1 - interval["start0"]
    if control["chrom"] != interval["chrom"] or not 0 <= offset < len(sequence):
        raise ValueError("Control site falls outside the reference interval")
    if sequence[offset] != control["ref"]:
        raise ValueError("Control reference base does not match")


def main() -> None:
    """Acquire and prepare the bundle, or verify the existing output offline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    p = json.loads((ROOT / "provenance.json").read_text())
    metadata = p["parameters"]["bundleMetadata"]
    record = p["outputs"]["reference"]
    destination = ROOT / record["path"]
    if args.verify_only:
        raw = destination.read_bytes()
        verify(raw, record)
        validate_sequence(json.loads(raw)["sequence"], metadata)
        return
    source = p["sources"][0]
    cached = ROOT / "download" / source["filename"]
    if cached.exists():
        dna = cached.read_bytes()
    else:
        with urlopen(source["url"], timeout=60) as response:
            body = response.read(2_000_001)
        if len(body) > 2_000_000:
            raise ValueError("UCSC response exceeds expected size bound")
        data = json.loads(body)
        interval = metadata["interval"]
        if (data["genome"], data["chrom"], data["start"], data["end"]) != (
            "hg38",
            interval["chrom"],
            interval["start0"],
            interval["end0"],
        ):
            raise ValueError("UCSC returned a different assembly or interval")
        dna = data["dna"].upper().encode("ascii")
    verify(dna, source)
    sequence = dna.decode("ascii")
    validate_sequence(sequence, metadata)
    raw = (
        json.dumps({**metadata, "sequence": sequence}, sort_keys=True, indent=2) + "\n"
    ).encode()
    verify(raw, record)
    write_atomic(cached, dna)
    write_atomic(destination, raw)


if __name__ == "__main__":
    main()
