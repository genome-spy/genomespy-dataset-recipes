#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
# /// script
# requires-python = "==3.14.*"
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
from collections import defaultdict
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


CHROMS = [f"chr{i}" for i in range(1, 23)] + ["chrX", "chrY", "chrM"]
FIELDS = [
    "assembly",
    "chrom",
    "start",
    "end",
    "strand",
    "symbol",
    "identifier",
    "score",
]


def gene_bodies(raw: bytes, assembly: str) -> list[dict[str, Any]]:
    """Merge touching or overlapping transcripts of one chromosome/strand/symbol."""
    transcripts = []
    for fields in csv.reader(
        io.StringIO(gzip.decompress(raw).decode()), delimiter="\t"
    ):
        if len(fields) != 16:
            raise ValueError("Expected 16 UCSC refGene columns")
        chrom, strand, symbol = fields[2], fields[3], fields[12]
        start, end = int(fields[4]), int(fields[5])
        if chrom not in CHROMS or strand not in ("+", "-"):
            continue
        if (
            not symbol.strip()
            or symbol in ("NA", "NaN", "NULL")
            or start < 0
            or end <= start
        ):
            continue
        transcripts.append((CHROMS.index(chrom), start, end, strand, symbol, fields[1]))
    transcripts.sort()
    groups: dict[tuple[str, str, str], list[tuple[int, int]]] = defaultdict(list)
    for chromosome, start, end, strand, symbol, _accession in transcripts:
        groups[(CHROMS[chromosome], strand, symbol)].append((start, end))
    result = []
    for (chrom, strand, symbol), intervals in groups.items():
        merged: list[list[int]] = []
        for start, end in intervals:
            if merged and start <= merged[-1][1]:
                merged[-1][1] = max(end, merged[-1][1])
                merged[-1][2] += 1
            else:
                merged.append([start, end, 1])
        for start, end, score in merged:
            result.append(
                dict(
                    assembly=assembly,
                    chrom=chrom,
                    start=start,
                    end=end,
                    strand=strand,
                    symbol=symbol,
                    identifier=f"{symbol}:{chrom}:{start}-{end}:{strand}",
                    score=score,
                )
            )
    return result


def prepare(sources: dict[str, bytes]) -> bytes:
    """Serialize both assemblies in accepted gene-group and interval order."""
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for assembly in ("hg19", "hg38"):
        writer.writerows(gene_bodies(sources[assembly], assembly))
    return gzip.compress(stream.getvalue().encode(), mtime=0)


def main() -> None:
    """Acquire pinned inputs and prepare data, or verify existing output offline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--source-dir", type=Path, default=ROOT / "download")
    args = parser.parse_args()
    provenance = json.loads((ROOT / "provenance.json").read_text())
    record = provenance["outputs"]["geneBodies"]
    destination = ROOT / record["path"]
    if args.verify_only:
        raw = destination.read_bytes()
    else:
        sources = {
            s["id"]: read_source(s, args.source_dir) for s in provenance["sources"]
        }
        raw = prepare(sources)
    verify(raw, record, "gene bodies")
    if hashlib.sha256(gzip.decompress(raw)).hexdigest() != record["decodedSha256"]:
        raise ValueError("Decoded gene-body table differs from provenance")
    if not args.verify_only:
        write_atomic(destination, raw)


if __name__ == "__main__":
    main()
