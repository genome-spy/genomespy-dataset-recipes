#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
# /// script
# requires-python = "==3.14.*"
# dependencies = [
#   "numpy==2.4.6", "pandas==3.0.3",
#   "scipy==1.17.1", "statsmodels==0.14.6",
# ]
# ///
"""Acquire pinned example inputs and verify byte-preserving recipe outputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
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


def table(raw: bytes) -> tuple[list[str], list[dict[str, str]]]:
    """Read the source CSV without changing its stored representation."""
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    return list(reader.fieldnames or []), list(reader)


def validate_tables(outputs: dict[str, bytes], expected: dict[str, Any]) -> None:
    """Check sample pairing and finite nonnegative length-scaled counts."""
    fields, samples = table(outputs["metadata"])
    if fields != expected["metadataColumns"] or len(samples) != 8:
        raise ValueError("Expected the original eight-sample metadata table")
    ids = [row["id"] for row in samples]
    if len(set(ids)) != 8:
        raise ValueError("Sample identifiers must be unique")
    pairs: dict[str, list[str]] = {}
    for row in samples:
        pairs.setdefault(row["celltype"], []).append(row["dex"])
    if len(pairs) != 4 or any(
        sorted(v) != ["control", "treated"] for v in pairs.values()
    ):
        raise ValueError("Expected four matched treated/control pairs")
    fields, counts = table(outputs["counts"])
    if fields != ["ensgene", *ids] or len(counts) != expected["geneCount"]:
        raise ValueError("Count columns or gene count changed")
    genes = set()
    for row in counts:
        if row["ensgene"] in genes or not row["ensgene"].startswith("ENSG"):
            raise ValueError("Duplicate or invalid gene identifier")
        genes.add(row["ensgene"])
        for sample in ids:
            value = float(row[sample])
            if not math.isfinite(value) or value < 0 or not value.is_integer():
                raise ValueError("Counts must be finite nonnegative rounded values")


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
            if "sourceId" in record
        }
        from review import prepare_review

        outputs["review"] = prepare_review(acquired, provenance["parameters"]["review"])
    for key, raw in outputs.items():
        verify(raw, provenance["outputs"][key], key)
    validate_tables(outputs, provenance["validation"])
    if not args.verify_only:
        for key, raw in outputs.items():
            write_atomic(ROOT / provenance["outputs"][key]["path"], raw)


if __name__ == "__main__":
    main()
