# mypy: ignore-errors
"""Wrangle MCCA transcriptome data into GenomeSpy metadata Zarr.

The source file is a zipped TSV where rows are Ensembl mouse gene IDs and
columns are MCCA sample IDs. This module maps Ensembl IDs to mouse gene symbols
using the pinned GENCODE M25 annotation, keeps the original Ensembl IDs as a
secondary lookup key, z-scores each gene across samples, and writes a
GenomeSpy-compatible Zarr v3 store. The Zarr layout follows the AnnData-style
convention used by GenomeSpy metadata sources: expression matrix in `X`, sample
IDs in `obs_names`, primary feature names in `var_names`, and additional
feature metadata under `var/`.
"""

from __future__ import annotations

import gzip
import math
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import zarr
from zarr.dtype import VariableLengthUTF8

from mcca_genomespy.values import is_missing_value

GENCODE_ATTRIBUTE_PATTERN = re.compile(r'(\S+) "([^"]*)";')


@dataclass(frozen=True)
class GeneInfo:
    symbol: str
    gene_type: str


# These expression-matrix Ensembl IDs are absent from GENCODE M25, but resolve
# to current mouse gene symbols. Keep this map explicit so wrangling remains
# reproducible with the pinned annotation release.
GENCODE_SYMBOL_FALLBACKS = {
    "ENSMUSG00000118667": GeneInfo("Ahnak2", "protein_coding"),
    "ENSMUSG00000118669": GeneInfo("Arvcf", "protein_coding"),
    "ENSMUSG00000118671": GeneInfo("Eppk1", "protein_coding"),
    "ENSMUSG00000118665": GeneInfo("Lin54", "protein_coding"),
    "ENSMUSG00000118672": GeneInfo("Muc4", "protein_coding"),
    "ENSMUSG00000118661": GeneInfo("Muc6", "protein_coding"),
    "ENSMUSG00000118668": GeneInfo("Rps6ka4", "protein_coding"),
    "ENSMUSG00000118663": GeneInfo("Afg2b", "protein_coding"),
    "ENSMUSG00000118662": GeneInfo("Tctn2", "protein_coding"),
    "ENSMUSG00000118664": GeneInfo("Tusc3", "protein_coding"),
}


def parse_expression_float(value: Any) -> float:
    if is_missing_value(value):
        return math.nan
    return float(value)


def parse_gencode_attributes(value: str) -> dict[str, str]:
    return dict(GENCODE_ATTRIBUTE_PATTERN.findall(value))


def unversioned_ensembl_id(value: str) -> str:
    return value.split(".", 1)[0]


def load_gencode_gene_map(path: Path) -> dict[str, GeneInfo]:
    gene_map: dict[str, GeneInfo] = {}
    with gzip.open(path, "rt") as file:
        for line in file:
            if line.startswith("#"):
                continue

            fields = line.rstrip("\n").split("\t")
            if len(fields) != 9 or fields[2] != "gene":
                continue

            attributes = parse_gencode_attributes(fields[8])
            gene_id = unversioned_ensembl_id(attributes["gene_id"])
            gene_map[gene_id] = GeneInfo(
                attributes["gene_name"],
                attributes["gene_type"],
            )
    return gene_map


def open_single_file_zip(path: Path):
    archive = zipfile.ZipFile(path)
    names = [name for name in archive.namelist() if not name.endswith("/")]
    if len(names) != 1:
        archive.close()
        raise ValueError("Transcriptome zip must contain exactly one file.")
    return archive, names[0]


def zscore_values(values: list[float]) -> list[float]:
    observed_values = [value for value in values if not math.isnan(value)]
    if not observed_values:
        return values

    mean = sum(observed_values) / len(observed_values)
    variance = sum((value - mean) ** 2 for value in observed_values) / len(
        observed_values
    )
    standard_deviation = math.sqrt(variance)
    if standard_deviation == 0:
        return [math.nan if math.isnan(value) else 0.0 for value in values]
    return [
        math.nan if math.isnan(value) else (value - mean) / standard_deviation
        for value in values
    ]


def create_string_array(
    group,
    name: str,
    values: list[str],
    chunk_size: int,
) -> None:
    array = group.create_array(
        name=name,
        shape=(len(values),),
        dtype=VariableLengthUTF8(),
        chunks=(min(chunk_size, len(values)),),
        overwrite=True,
    )
    array[:] = np.asarray(values, dtype=object)


def resolve_gene_info(gene_id: str, gene_map: dict[str, GeneInfo] | None) -> GeneInfo:
    if gene_map is None:
        return GeneInfo(gene_id, "")

    unversioned_gene_id = unversioned_ensembl_id(gene_id)
    gene_info = gene_map.get(unversioned_gene_id)
    if gene_info is not None:
        return gene_info

    fallback = GENCODE_SYMBOL_FALLBACKS.get(unversioned_gene_id)
    if fallback is not None:
        return fallback

    raise ValueError("No gene symbol found for transcriptome gene id: " + gene_id)


def write_transcriptome_zarr(
    zip_path: Path,
    output_dir: Path,
    gene_map: dict[str, GeneInfo] | None = None,
    row_chunk_size: int = 128,
    column_chunk_size: int = 512,
) -> dict[str, int]:
    archive, filename = open_single_file_zip(zip_path)
    try:
        with archive.open(filename) as raw:
            text_rows = (
                line.decode("utf-8-sig").rstrip("\n\r").split("\t") for line in raw
            )
            header = next(text_rows)
            sample_ids = header[1:]
            if len(sample_ids) != len(set(sample_ids)):
                raise ValueError("Transcriptome table contains duplicate sample ids.")

            matrix: list[list[float]] = [[] for _ in sample_ids]
            gene_ids = []
            gene_symbols = []
            gene_types = []
            seen_genes = set()
            seen_symbols = set()

            for row in text_rows:
                if len(row) != len(header):
                    raise ValueError(
                        "Transcriptome row for " + row[0] + " has wrong length."
                    )
                gene_id = row[0]
                if gene_id in seen_genes:
                    raise ValueError("Duplicate transcriptome gene id: " + gene_id)
                seen_genes.add(gene_id)

                gene_info = resolve_gene_info(gene_id, gene_map)
                if gene_info.symbol in seen_symbols:
                    raise ValueError(
                        "Duplicate transcriptome gene symbol: " + gene_info.symbol
                    )
                seen_symbols.add(gene_info.symbol)

                gene_ids.append(gene_id)
                gene_symbols.append(gene_info.symbol)
                gene_types.append(gene_info.gene_type)
                values = [parse_expression_float(value) for value in row[1:]]
                zscores = zscore_values(values)
                for index, value in enumerate(zscores):
                    matrix[index].append(value)
    finally:
        archive.close()

    if output_dir.exists():
        shutil.rmtree(output_dir)

    sample_count = len(sample_ids)
    gene_count = len(gene_ids)
    matrix_array = np.asarray(matrix, dtype=np.float32)
    root = zarr.open_group(
        store=zarr.storage.LocalStore(output_dir),
        mode="w",
        zarr_format=3,
    )
    root.create_array(
        name="X",
        data=matrix_array,
        chunks=(
            min(row_chunk_size, sample_count),
            min(column_chunk_size, gene_count),
        ),
        overwrite=True,
    )
    create_string_array(root, "obs_names", sample_ids, row_chunk_size)
    create_string_array(root, "var_names", gene_symbols, column_chunk_size)

    var_group = root.create_group("var", overwrite=True)
    create_string_array(var_group, "symbol", gene_symbols, column_chunk_size)
    create_string_array(var_group, "ensembl_id", gene_ids, column_chunk_size)
    create_string_array(var_group, "gene_type", gene_types, column_chunk_size)
    root.attrs.update(
        {
            "layout": "GenomeSpy expression v3",
            "X_shape": [sample_count, gene_count],
            "X_chunks": [
                min(row_chunk_size, sample_count),
                min(column_chunk_size, gene_count),
            ],
        }
    )

    return {
        "samples": sample_count,
        "genes": gene_count,
        "matrix_cells": sample_count * gene_count,
    }
