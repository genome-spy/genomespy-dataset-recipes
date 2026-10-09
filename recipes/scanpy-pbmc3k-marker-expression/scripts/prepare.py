#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
# /// script
# requires-python = "==3.14.3"
# dependencies = ["anndata==0.12.19", "numpy==2.4.6", "scipy==1.17.1", "h5py==3.16.0"]
# ///
"""Run the pinned upstream PBMC producer and verify its prepared data contract."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def verify(raw: bytes, record: dict[str, Any]) -> None:
    """Reject incomplete or changed content."""
    if (
        len(raw) != record["fileSizeBytes"]
        or hashlib.sha256(raw).hexdigest() != record["sha256"]
    ):
        raise ValueError("Content differs from pinned size or SHA-256")


def write_atomic(path: Path, raw: bytes) -> None:
    """Expose only a complete local file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(raw)
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def acquire(record: dict[str, Any]) -> Path:
    """Download a pinned input once; reject a corrupt cache without replacing it."""
    path = ROOT / "download" / record["filename"]
    if path.exists():
        raw = path.read_bytes()
    else:
        with urlopen(record["url"], timeout=120) as response:
            raw = response.read(record["fileSizeBytes"] + 1)
    verify(raw, record)
    if not path.exists():
        write_atomic(path, raw)
    return path


def validate_bundle(data: dict[str, Any]) -> None:
    """Check row alignment, expression summaries, and plotting contracts."""
    cells = data["cells"]
    count = len(cells)
    if len({c["cell"] for c in cells}) != count:
        raise ValueError("Duplicate cell identifiers")
    if [c["cell_order"] for c in cells] != list(range(count)):
        raise ValueError("Cell order is not contiguous")
    for key, width in [
        ("expression", len(data["markers"])),
        ("umap_expression", len(data["umap_genes"])),
        ("umap", 2),
    ]:
        rows = data[key]
        if len(rows) != count or any(len(row) != width for row in rows):
            raise ValueError(f"{key}: matrix dimensions do not match cells and genes")
        if any(
            not math.isfinite(x) or (key != "umap" and x < 0)
            for row in rows
            for x in row
        ):
            raise ValueError(f"{key}: invalid numeric values")
    cursor = 0
    for group in data["groups"]:
        start, end = group["start"], group["end"]
        if start != cursor or end <= start or end - start != group["count"]:
            raise ValueError("Group intervals do not partition the cells")
        if any(c["cell_type"] != group["cell_type"] for c in cells[start:end]):
            raise ValueError("Group labels disagree with their cell interval")
        cursor = end
    if cursor != count:
        raise ValueError("Groups do not cover every cell")
    groups = {g["cell_type"]: g for g in data["groups"]}
    markers = [m["gene"] for m in data["markers"]]
    expected = {(g, gene) for g in groups for gene in markers}
    if {(m["cell_type"], m["gene"]) for m in data["means"]} != expected or len(
        data["means"]
    ) != len(expected):
        raise ValueError("Group mean table is incomplete or duplicated")
    for mean in data["means"]:
        group = groups[mean["cell_type"]]
        column = markers.index(mean["gene"])
        values = [
            row[column] for row in data["expression"][group["start"] : group["end"]]
        ]
        if not math.isclose(
            mean["mean_expression"],
            math.fsum(values) / len(values),
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError("Group mean differs from cell expression")
    for axis, bounds in enumerate(
        [data["umap_domains"]["x"], data["umap_domains"]["y"]]
    ):
        if not all(bounds[0] <= row[axis] <= bounds[1] for row in data["umap"]):
            raise ValueError("UMAP domain clips source coordinates")
    if any(c["n_counts"] < 0 or c["n_counts"] > data["n_counts_limit"] for c in cells):
        raise ValueError("Invalid total-count display range")


def canonical_gzip(payload: bytes) -> bytes:
    """Compress without timestamps, filenames, or a platform-specific OS byte."""
    stream = io.BytesIO()
    with gzip.GzipFile(
        filename="", mode="wb", fileobj=stream, mtime=0, compresslevel=9
    ) as compressed:
        compressed.write(payload)
    return stream.getvalue()


def verify_bundle(raw: bytes, record: dict[str, Any]) -> None:
    """Verify compressed identity and the independent decoded contract."""
    verify(raw, record)
    payload = gzip.decompress(raw)
    if hashlib.sha256(payload).hexdigest() != record["decodedSha256"]:
        raise ValueError("Decoded data differs from the accepted Python bundle")
    validate_bundle(json.loads(payload))


def main() -> None:
    """Reproduce the release, or verify all existing outputs offline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    provenance = json.loads((ROOT / "provenance.json").read_text())
    outputs = provenance["outputs"]
    if args.verify_only:
        for record in outputs.values():
            verify((ROOT / record["path"]).read_bytes(), record)
        verify_bundle(
            (ROOT / outputs["bundle"]["path"]).read_bytes(), outputs["bundle"]
        )
        return
    inputs = {s["id"]: acquire(s) for s in provenance["sources"]}
    workspace = ROOT / "work" / "producer"
    destinations = {
        "producer": "tools/prepare_pbmc_gallery_data.py",
        "h5ad": "tmp/pbmc/pbmc3k.h5ad",
        "producerLicense": "LICENSE",
    }
    for key, relative in destinations.items():
        target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(inputs[key], target)
    produced = workspace / "src/genome_spy/datasets/data/pbmc_markers.json.gz"
    produced.parent.mkdir(parents=True, exist_ok=True)
    produced.unlink(missing_ok=True)
    subprocess.run(
        [sys.executable, str(workspace / destinations["producer"])],
        check=True,
        cwd=workspace,
    )
    raw = canonical_gzip(gzip.decompress(produced.read_bytes()))
    verify_bundle(raw, outputs["bundle"])
    write_atomic(ROOT / outputs["bundle"]["path"], raw)
    for record in outputs.values():
        if "sourceId" in record:
            notice = inputs[record["sourceId"]].read_bytes()
            verify(notice, record)
            write_atomic(ROOT / record["path"], notice)


if __name__ == "__main__":
    main()
