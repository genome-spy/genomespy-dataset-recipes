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
import gzip
import hashlib
import io
import json
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
    """Check the single-sample SNV table without modifying its representation."""
    reader = csv.DictReader(
        io.StringIO(gzip.decompress(outputs["mutations"]).decode("utf-8")),
        delimiter="\t",
    )
    rows = list(reader)
    if reader.fieldnames != expected["columns"] or len(rows) != expected["recordCount"]:
        raise ValueError("BRCA columns or record count changed")
    chromosomes = set()
    for row in rows:
        if row["Tumor_Sample_Barcode"] != expected["sample"]:
            raise ValueError("Unexpected BRCA sample")
        if row["Variant_Type"] != "SNP":
            raise ValueError("Expected single-nucleotide variants")
        start, end = int(row["Start_Position"]), int(row["End_Position"])
        if start < 1 or start != end:
            raise ValueError("Invalid one-based SNV coordinates")
        ref, alt = row["Reference_Allele"], row["Tumor_Seq_Allele2"]
        if (
            ref not in ("A", "C", "G", "T")
            or alt not in ("A", "C", "G", "T")
            or ref == alt
        ):
            raise ValueError("Invalid SNV alleles")
        chromosomes.add(row["Chromosome"])
    if chromosomes != set(expected["chromosomes"]):
        raise ValueError("BRCA chromosome set changed")


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
