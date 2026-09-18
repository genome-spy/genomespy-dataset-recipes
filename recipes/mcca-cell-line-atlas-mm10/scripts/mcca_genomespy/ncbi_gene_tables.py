# mypy: ignore-errors
"""Read large NCBI Gene tables without materializing all species."""

from __future__ import annotations

import gzip
from collections.abc import Iterable
from pathlib import Path

import polars as pl

GENE2ENSEMBL_COLUMNS = [
    "tax_id",
    "GeneID",
    "Ensembl_gene_identifier",
    "RNA_nucleotide_accession.version",
    "Ensembl_rna_identifier",
    "protein_accession.version",
    "Ensembl_protein_identifier",
]
GENE2PUBMED_COLUMNS = ["tax_id", "GeneID", "PubMed_ID"]


def iter_tsv_rows(path: Path) -> Iterable[list[str]]:
    with gzip.open(path, "rt") as file:
        for line in file:
            if not line.startswith("#"):
                yield line.rstrip("\n").split("\t")


def filter_taxon_rows(
    rows: Iterable[list[str]],
    columns: list[str],
    tax_id: int,
    selected_columns: list[str],
) -> pl.DataFrame:
    tax_id_text = str(tax_id)
    selected_indexes = [columns.index(column) for column in selected_columns]
    records = []

    for row in rows:
        if row[0] == tax_id_text:
            records.append(
                {
                    column: row[index]
                    for column, index in zip(
                        selected_columns,
                        selected_indexes,
                        strict=True,
                    )
                }
            )

    return pl.DataFrame(records, schema=selected_columns, orient="row")


def read_taxon_table(
    path: Path,
    columns: list[str],
    tax_id: int,
    selected_columns: list[str],
) -> pl.DataFrame:
    return filter_taxon_rows(
        iter_tsv_rows(path),
        columns,
        tax_id,
        selected_columns,
    )
