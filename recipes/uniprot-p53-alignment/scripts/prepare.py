#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Reproduce the pinned 34-sequence P53 alignment using MAFFT 7.526."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def verify(raw: bytes, record: dict[str, Any]) -> None:
    """Require the accepted size and digest."""
    if (
        len(raw) != record["fileSizeBytes"]
        or hashlib.sha256(raw).hexdigest() != record["sha256"]
    ):
        raise ValueError("Content differs from the pinned size or SHA-256")


def write_atomic(path: Path, raw: bytes) -> None:
    """Expose a complete validated file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(raw)
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def parse_fasta(raw: bytes) -> dict[str, str]:
    """Parse FASTA in input order, rejecting empty or duplicate records."""
    records: dict[str, str] = {}
    header = ""
    for line in raw.decode("ascii").splitlines():
        if line.startswith(">"):
            header = line[1:]
            if not header or header in records:
                raise ValueError("Empty or duplicate FASTA header")
            records[header] = ""
        elif line:
            if not header:
                raise ValueError("FASTA sequence precedes its header")
            records[header] += line.upper()
    if not records or any(not sequence for sequence in records.values()):
        raise ValueError("Empty FASTA record")
    return records


def validate_alignment(raw: bytes, source: bytes | None = None) -> None:
    """Require a rectangular alignment and unchanged sequences and order."""
    aligned = parse_fasta(raw)
    if len(aligned) != 34 or len({len(s) for s in aligned.values()}) != 1:
        raise ValueError("Expected a rectangular 34-sequence alignment")
    if any(set(s) - set("ACDEFGHIKLMNPQRSTVWY-") for s in aligned.values()):
        raise ValueError("Unexpected protein alignment alphabet")
    if source is not None:
        original = parse_fasta(source)
        if list(aligned) != list(original):
            raise ValueError("Alignment changed sequence headers or order")
        if {h: s.replace("-", "") for h, s in aligned.items()} != original:
            raise ValueError("Alignment changed source residues")


def acquire(source: dict[str, Any]) -> tuple[Path, bytes]:
    """Acquire a pinned source or reuse its verified local cache."""
    cached = ROOT / "download" / source["filename"]
    if cached.exists():
        raw = cached.read_bytes()
    else:
        with urlopen(source["url"], timeout=60) as response:
            raw = response.read(source["fileSizeBytes"] + 1)
    verify(raw, source)
    write_atomic(cached, raw)
    return cached, raw


def main() -> None:
    """Prepare from the pinned FASTA, or verify the accepted output offline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mafft", default="mafft-linsi", help="MAFFT 7.526 mafft-linsi executable"
    )
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    p = json.loads((ROOT / "provenance.json").read_text())
    output = p["outputs"]["alignment"]
    destination = ROOT / output["path"]
    if args.verify_only:
        for record in p["outputs"].values():
            verify((ROOT / record["path"]).read_bytes(), record)
        validate_alignment(destination.read_bytes())
        return
    cached, raw = acquire(p["sources"][0])
    _, notice = acquire(p["sources"][1])
    if Path(args.mafft).name not in {"mafft-linsi", "linsi"}:
        raise ValueError("Use the mafft-linsi executable to select L-INS-i")
    version = subprocess.run(
        [args.mafft, "--version"], capture_output=True, text=True, check=True
    )
    if not (version.stdout + version.stderr).strip().startswith("v7.526 ("):
        raise ValueError("MAFFT 7.526 is required to reproduce this release")
    aligned = subprocess.run(
        [args.mafft, *p["parameters"]["arguments"], str(cached)],
        capture_output=True,
        check=True,
    ).stdout
    validate_alignment(aligned, raw)
    verify(aligned, output)
    write_atomic(destination, aligned)
    write_atomic(ROOT / p["outputs"]["notice"]["path"], notice)


if __name__ == "__main__":
    main()
