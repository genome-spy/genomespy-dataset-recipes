# mypy: ignore-errors
"""Compress gene exon models for GenomeSpy gene tracks."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import polars as pl

COMPRESSED_COLUMNS = [
    "symbol",
    "chrom",
    "start",
    "length",
    "strand",
    "score",
    "exons",
]


def split_exons(exon_string: str) -> list[int]:
    return [int(value) for value in exon_string.split(",") if value != ""]


def compute_union(
    exon_starts: list[int], exon_ends: list[int]
) -> list[tuple[int, int]]:
    edges = [(value, 1) for value in exon_starts] + [(value, -1) for value in exon_ends]
    edges.sort(key=lambda edge: edge[0])

    intervals = []
    height = 0
    start = 0
    for position, delta in edges:
        if height == 0:
            start = position
        height += delta
        if height == 0:
            intervals.append((start, position))
    return intervals


def run_length_encode(reference: int, intervals: list[tuple[int, int]]) -> list[int]:
    deltas = []
    for start, end in intervals:
        start_delta = start - reference
        deltas.append(start_delta)
        reference += start_delta

        end_delta = end - reference
        deltas.append(end_delta)
        reference += end_delta
    return deltas


def disjoint_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return row["geneName"], row["chr"], row["strand"]


def merge_gene_annotations(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    genes: dict[tuple[str, str, str], list[dict[str, Any]]] = {}

    for row in rows:
        key = disjoint_key(row)
        tx_start = int(row["txStart"])
        tx_end = int(row["txEnd"])
        match = None
        for gene in genes.get(key, []):
            if gene["txEnd"] >= tx_start and gene["txStart"] <= tx_end:
                match = gene
                break

        exon_starts = split_exons(row["exonStarts"])
        exon_ends = split_exons(row["exonEnds"])
        if match is None:
            genes.setdefault(key, []).append(
                {
                    "symbol": row["geneName"],
                    "chrom": row["chr"],
                    "txStart": tx_start,
                    "txEnd": tx_end,
                    "strand": row["strand"],
                    "score": int(row["citationCount"]),
                    "exonStarts": exon_starts,
                    "exonEnds": exon_ends,
                }
            )
        else:
            match["txStart"] = min(match["txStart"], tx_start)
            match["txEnd"] = max(match["txEnd"], tx_end)
            match["score"] = max(match["score"], int(row["citationCount"]))
            match["exonStarts"].extend(exon_starts)
            match["exonEnds"].extend(exon_ends)

    return [gene for disjoint_genes in genes.values() for gene in disjoint_genes]


def compress_gene_annotations(annotations: pl.DataFrame) -> pl.DataFrame:
    compressed_rows = []
    for gene in merge_gene_annotations(annotations.to_dicts()):
        intervals = compute_union(gene["exonStarts"], gene["exonEnds"])
        exons = run_length_encode(gene["txStart"], intervals)
        compressed_rows.append(
            {
                "symbol": gene["symbol"],
                "chrom": gene["chrom"],
                "start": gene["txStart"],
                "length": gene["txEnd"] - gene["txStart"],
                "strand": gene["strand"],
                "score": gene["score"],
                "exons": ",".join(str(value) for value in exons),
            }
        )

    return pl.DataFrame(compressed_rows).select(COMPRESSED_COLUMNS)
