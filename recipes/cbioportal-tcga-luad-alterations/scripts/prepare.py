#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Acquire pinned example inputs and verify byte-preserving recipe outputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def verify(raw: bytes, record: dict[str, Any], label: str) -> None:
    """Reject changed or truncated input before accepting it."""
    if len(raw) != record["fileSizeBytes"]:
        raise ValueError(f"{label}: byte size differs from provenance")
    if hashlib.sha256(raw).hexdigest() != record["sha256"]:
        raise ValueError(f"{label}: SHA-256 differs from provenance")


def write_atomic(path: Path, raw: bytes) -> None:
    """Expose only complete verified files to other processes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(raw)
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def read_source(record: dict[str, Any], source_dir: Path) -> bytes:
    """Read a verified cached source or download its exact recorded identity."""
    path = source_dir / record["filename"]
    if path.exists():
        raw = path.read_bytes()
    else:
        request = Request(record["url"], headers={"Accept-Encoding": "identity"})
        with urlopen(request, timeout=60) as response:
            raw = response.read(record["fileSizeBytes"] + 1)
    verify(raw, record, record["filename"])
    if not path.exists():
        write_atomic(path, raw)
    return raw


def validate_tables(outputs: dict[str, bytes], expected: dict[str, Any]) -> None:
    """Check the wide historical export without interpreting its assay values."""
    rows = list(
        csv.reader(io.StringIO(outputs["alterations"].decode("utf-8")), delimiter="\t")
    )
    if not rows or rows[0][:2] != ["track_name", "track_type"]:
        raise ValueError("Invalid LUAD metadata columns")
    samples = rows[0][2:]
    if len(samples) != expected["sampleCount"] or len(set(samples)) != len(samples):
        raise ValueError("LUAD sample columns must be unique and complete")
    if any(not sample.startswith("TCGA-") for sample in samples):
        raise ValueError("Invalid LUAD sample identifier")
    tracks = rows[1:]
    if len(tracks) != expected["trackCount"] or any(
        len(row) != len(rows[0]) for row in tracks
    ):
        raise ValueError("LUAD dimensions changed")
    if dict(Counter(row[1] for row in tracks)) != expected["trackTypes"]:
        raise ValueError("LUAD track types changed")
    identities = [(row[0], row[1]) for row in tracks]
    if len(set(identities)) != len(identities):
        raise ValueError("Duplicate LUAD track identity")
    if tuple(expected["historicalMicrobiomeTrack"]) not in identities:
        raise ValueError(
            "Historical microbiome track missing; do not silently replace the export"
        )


def main() -> None:
    """Prepare all outputs, or validate an existing release without network I/O."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--source-dir", type=Path, default=ROOT / "download")
    args = parser.parse_args()
    provenance = json.loads((ROOT / "provenance.json").read_text())
    if args.verify_only:
        outputs = {
            key: (ROOT / record["path"]).read_bytes()
            for key, record in provenance["outputs"].items()
        }
    else:
        acquired = {
            source["id"]: read_source(source, args.source_dir)
            for source in provenance["sources"]
        }
        outputs = {
            key: acquired[record["sourceId"]]
            for key, record in provenance["outputs"].items()
        }
    for key, raw in outputs.items():
        verify(raw, provenance["outputs"][key], key)
    validate_tables(outputs, provenance["validation"])
    if not args.verify_only:
        for key, raw in outputs.items():
            write_atomic(ROOT / provenance["outputs"][key]["path"], raw)


if __name__ == "__main__":
    main()
