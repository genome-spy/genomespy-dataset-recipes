# mypy: follow_imports=skip, ignore_missing_imports=True
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "numpy==2.4.6",
#   "openpyxl==3.1.5",
#   "polars==1.40.1",
#   "pyarrow==24.0.0",
#   "pytest==8.4.2",
#   "zarr==3.2.1",
# ]
# ///
"""Prepare and verify the MCCA GenomeSpy recipe outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq  # type: ignore[import-not-found]
import pytest
import zarr  # type: ignore[import-not-found]
from mcca_genomespy.download import download_files
from mcca_genomespy.gene_annotations import (
    GENCODE_GENES_OUTPUT_FILENAME,
    generate_gencode_gene_annotations,
)
from mcca_genomespy.wrangle import wrangle

RECIPE_ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_DIR = RECIPE_ROOT / "download"
OUTPUT_DIR = RECIPE_ROOT / "output"
PROVENANCE_PATH = RECIPE_ROOT / "provenance.json"


def sha256(path: Path) -> str:
    """Return a file's SHA-256 digest."""

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_identity(path: Path, identity: dict[str, Any]) -> None:
    """Verify a file against a size and SHA-256 identity."""

    if not path.is_file():
        raise FileNotFoundError(path)
    expected_size = identity["fileSizeBytes"]
    actual_size = path.stat().st_size
    if actual_size != expected_size:
        raise ValueError(f"Wrong size for {path}: {actual_size} != {expected_size}")
    expected_sha256 = identity["sha256"]
    actual_sha256 = sha256(path)
    if actual_sha256 != expected_sha256:
        raise ValueError(
            f"Wrong SHA-256 for {path}: {actual_sha256} != {expected_sha256}"
        )


def load_provenance() -> dict[str, Any]:
    """Load the accepted-run record."""

    return json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))


def source_paths(provenance: dict[str, Any]) -> list[tuple[Path, dict[str, Any]]]:
    """Resolve all source identities to their local recipe paths."""

    paths = []
    for source in provenance["sources"]:
        relative_path = source["localPath"]
        paths.append((RECIPE_ROOT / relative_path, source))
    return paths


def verify_sources(provenance: dict[str, Any]) -> None:
    """Verify every accepted input."""

    for path, identity in source_paths(provenance):
        verify_identity(path, identity)


def validate_parquet(path: Path, expected_rows: int, expected_columns: int) -> None:
    """Validate a Parquet table's dimensions."""

    table = pq.read_table(path)
    if (table.num_rows, table.num_columns) != (expected_rows, expected_columns):
        raise ValueError(
            f"Unexpected Parquet dimensions for {path}: "
            f"{table.num_rows}x{table.num_columns}"
        )


def validate_scientific_contract(provenance: dict[str, Any]) -> None:
    """Validate table dimensions and the transcriptome array contract."""

    for output in provenance["outputs"].values():
        path = RECIPE_ROOT / output["path"]
        if output.get("format") == "parquet":
            validate_parquet(path, output["recordCount"], output["fieldCount"])

    expression = provenance["outputs"]["expression"]
    root = zarr.open_group(OUTPUT_DIR / "processed" / "expression.zarr", mode="r")
    expected_shape = tuple(expression["matrixShape"])
    if root["X"].shape != expected_shape:
        raise ValueError(
            f"Unexpected expression shape: {root['X'].shape} != {expected_shape}"
        )
    if root["obs_names"].shape != (expected_shape[0],):
        raise ValueError("Expression sample identifiers do not match the matrix")
    if root["var_names"].shape != (expected_shape[1],):
        raise ValueError("Expression feature identifiers do not match the matrix")


def verify_outputs(provenance: dict[str, Any]) -> None:
    """Verify every publication artifact and its scientific contract."""

    artifacts = provenance["distribution"]["artifacts"]
    for relative_path, identity in artifacts.items():
        verify_identity(RECIPE_ROOT / relative_path, identity)
    validate_scientific_contract(provenance)


def prepare(force_download: bool) -> None:
    """Download accepted inputs and generate all recipe outputs."""

    provenance = load_provenance()
    download_files(DOWNLOAD_DIR, OUTPUT_DIR, force=force_download)
    verify_sources(provenance)
    wrangle(DOWNLOAD_DIR, OUTPUT_DIR / "processed")
    gene_count = generate_gencode_gene_annotations(
        DOWNLOAD_DIR,
        OUTPUT_DIR / "external-data" / GENCODE_GENES_OUTPUT_FILENAME,
    )
    expected_gene_count = provenance["outputs"]["genes"]["recordCount"]
    if gene_count != expected_gene_count:
        raise ValueError(
            f"Unexpected gene count: {gene_count} != {expected_gene_count}"
        )
    verify_outputs(provenance)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run the migrated recipe's focused unit and spec tests.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify existing accepted inputs and outputs without generating files.",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Refresh downloads before verifying their pinned identities.",
    )
    return parser.parse_args()


def main() -> None:
    """Run preparation or verification."""

    args = parse_args()
    if args.test:
        raise SystemExit(pytest.main([str(RECIPE_ROOT / "tests"), "-q"]))
    provenance = load_provenance()
    if args.verify_only:
        verify_sources(provenance)
        verify_outputs(provenance)
    else:
        prepare(args.force_download)
    print("MCCA recipe verification passed.")


if __name__ == "__main__":
    main()
