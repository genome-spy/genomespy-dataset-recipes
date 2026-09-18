# mypy: ignore-errors
"""Build GenomeSpy GENCODE gene annotations with HiGlass-style scores.

This module adapts the citation-count scoring idea from the HiGlass gene
annotation preparation guide:
https://docs.higlass.io/data_preparation.html#gene-annotation-tracks

It replaces the linked shell snippets with a cross-platform Python/Polars
implementation. It uses GENCODE mouse M25 transcript models, scores genes by
NCBI PubMed citation count through `gene2ensembl`, and writes the compressed
GenomeSpy gene annotation TSV format used by the `flattenCompressedExons`
transform.
"""

from __future__ import annotations

import argparse
import gzip
import re
from pathlib import Path
from typing import TextIO

import polars as pl

from mcca_genomespy.exon_compression import compress_gene_annotations
from mcca_genomespy.ncbi_gene_tables import (
    GENE2ENSEMBL_COLUMNS,
    GENE2PUBMED_COLUMNS,
    read_taxon_table,
)

GENE_ANNOTATION_COLUMNS = [
    "chr",
    "txStart",
    "txEnd",
    "geneName",
    "citationCount",
    "strand",
    "refseqId",
    "geneId",
    "geneType",
    "geneDesc",
    "cdsStart",
    "cdsEnd",
    "exonStarts",
    "exonEnds",
]
MOUSE_TAX_ID = 10090
GENCODE_GTF_FILENAME = "gencode.vM25.annotation.gtf.gz"
GENE2ENSEMBL_FILENAME = "gene2ensembl.gz"
GENE2PUBMED_FILENAME = "gene2pubmed.gz"
GENCODE_GENES_OUTPUT_FILENAME = "gencodeGenes-mm10.tsv"
GENCODE_ATTRIBUTE_PATTERN = re.compile(r'(\S+) "([^"]*)";')


def canonical_mm10_chroms() -> set[str]:
    return {f"chr{chrom}" for chrom in range(1, 20)} | {"chrX", "chrY"}


def open_text(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, "rt")
    return path.open()


def parse_gencode_attributes(value: str) -> dict[str, str]:
    return dict(GENCODE_ATTRIBUTE_PATTERN.findall(value))


def unversioned_ensembl_id(value: str) -> str:
    return value.split(".", 1)[0]


def parse_gencode_gtf(path: Path, canonical_chroms: set[str]) -> pl.DataFrame:
    genes: dict[str, dict[str, object]] = {}

    with open_text(path) as file:
        for line in file:
            if line.startswith("#"):
                continue

            fields = line.rstrip("\n").split("\t")
            if len(fields) != 9 or fields[0] not in canonical_chroms:
                continue

            feature = fields[2]
            if feature != "gene" and feature != "exon":
                continue

            attributes = parse_gencode_attributes(fields[8])
            gene_id = unversioned_ensembl_id(attributes["gene_id"])
            start = int(fields[3]) - 1
            end = int(fields[4])

            gene = genes.setdefault(
                gene_id,
                {
                    "ensemblGeneId": gene_id,
                    "chr": fields[0],
                    "txStart": start,
                    "txEnd": end,
                    "geneName": attributes["gene_name"],
                    "strand": fields[6],
                    "geneType": attributes["gene_type"],
                    "exonStarts": [],
                    "exonEnds": [],
                },
            )

            if feature == "gene":
                gene["txStart"] = min(int(gene["txStart"]), start)
                gene["txEnd"] = max(int(gene["txEnd"]), end)
            else:
                gene["exonStarts"].append(start)
                gene["exonEnds"].append(end)

    rows = []
    for gene in genes.values():
        exon_pairs = sorted(
            zip(gene["exonStarts"], gene["exonEnds"], strict=True),
            key=lambda pair: pair[0],
        )
        rows.append(
            {
                **gene,
                "exonStarts": "".join(f"{start}," for start, _ in exon_pairs),
                "exonEnds": "".join(f"{end}," for _, end in exon_pairs),
            }
        )

    return (
        pl.DataFrame(rows)
        .select(
            [
                "ensemblGeneId",
                "chr",
                "txStart",
                "txEnd",
                "geneName",
                "strand",
                "geneType",
                "exonStarts",
                "exonEnds",
            ]
        )
        .sort("chr", "txStart", "txEnd", "geneName")
    )


def build_gene_annotations_bed(
    gencode: pl.DataFrame,
    gene2ensembl: pl.DataFrame,
    gene2pubmed: pl.DataFrame,
) -> pl.DataFrame:
    citation_counts = (
        gene2pubmed.group_by("GeneID").len().rename({"len": "citationCount"})
    )
    gene_scores = (
        gene2ensembl.filter(pl.col("Ensembl_gene_identifier") != "-")
        .select(
            "GeneID",
            pl.col("Ensembl_gene_identifier").alias("ensemblGeneId"),
        )
        .unique()
        .join(citation_counts, on="GeneID", how="left")
        .with_columns(pl.col("citationCount").fill_null(0).cast(pl.Int64))
        .group_by("ensemblGeneId")
        .agg(
            pl.col("GeneID").sort().first().alias("geneId"),
            pl.col("citationCount").max(),
        )
    )

    return (
        gencode.join(gene_scores, on="ensemblGeneId", how="left")
        # HiGlass' shell snippets use an inner join with citation counts. Keep
        # uncited or unmapped GENCODE genes instead and assign score 0 so
        # obscure genes remain searchable and visible when zoomed in.
        .with_columns(
            pl.col("citationCount").fill_null(0).cast(pl.Int64),
            pl.coalesce("geneId", "ensemblGeneId").alias("geneId"),
            pl.col("ensemblGeneId").alias("refseqId"),
            pl.lit("").alias("geneDesc"),
            pl.col("txStart").alias("cdsStart"),
            pl.col("txEnd").alias("cdsEnd"),
        )
        .select(GENE_ANNOTATION_COLUMNS)
        .sort("chr", "txStart", "txEnd", "geneName", "refseqId")
    )


def write_compressed_annotations(path: Path, annotations: pl.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    annotations.write_csv(path, separator="\t", include_header=True)


def write_gene_annotations_bed(path: Path, annotations: pl.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    annotations.write_csv(
        path,
        separator="\t",
        include_header=False,
        quote_style="never",
    )


def provenance_path_for(output_path: Path) -> Path:
    return output_path.with_suffix(".provenance.txt")


def write_gene_annotation_provenance(
    output_path: Path,
    source_filenames: list[str],
    row_count: int,
) -> None:
    lines = [
        "GenomeSpy GENCODE gene annotation provenance",
        "Assembly: mm10",
        "Annotation: GENCODE mouse M25",
        f"NCBI tax_id: {MOUSE_TAX_ID}",
        f"Output: {output_path.name}",
        f"Rows: {row_count}",
        "Sources:",
        *[f"- {filename}" for filename in source_filenames],
        "",
    ]
    path = provenance_path_for(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))


def generate_gencode_gene_annotations(
    raw_dir: Path,
    output_path: Path,
    tax_id: int = MOUSE_TAX_ID,
    canonical_chroms: set[str] | None = None,
    debug_bed_path: Path | None = None,
) -> int:
    canonical_chroms = canonical_chroms or canonical_mm10_chroms()
    gene2ensembl = read_taxon_table(
        raw_dir / GENE2ENSEMBL_FILENAME,
        GENE2ENSEMBL_COLUMNS,
        tax_id,
        ["GeneID", "Ensembl_gene_identifier"],
    )
    gene2pubmed = read_taxon_table(
        raw_dir / GENE2PUBMED_FILENAME,
        GENE2PUBMED_COLUMNS,
        tax_id,
        ["GeneID", "PubMed_ID"],
    )
    annotations = build_gene_annotations_bed(
        parse_gencode_gtf(raw_dir / GENCODE_GTF_FILENAME, canonical_chroms),
        gene2ensembl,
        gene2pubmed,
    )
    if debug_bed_path is not None:
        write_gene_annotations_bed(debug_bed_path, annotations)

    compressed = compress_gene_annotations(annotations)
    write_compressed_annotations(output_path, compressed)
    write_gene_annotation_provenance(
        output_path,
        [
            GENCODE_GTF_FILENAME,
            GENE2ENSEMBL_FILENAME,
            GENE2PUBMED_FILENAME,
        ],
        compressed.height,
    )
    return compressed.height


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate compressed mm10 GENCODE M25 gene annotations for "
            "GenomeSpy using NCBI mouse taxon 10090 PubMed counts as scores."
        )
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "download",
        help="Directory containing downloaded GENCODE and NCBI gene annotation files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            Path(__file__).resolve().parents[2]
            / "output"
            / "external-data"
            / GENCODE_GENES_OUTPUT_FILENAME
        ),
        help="Output path for compressed GenomeSpy GENCODE annotations.",
    )
    parser.add_argument(
        "--debug-bed",
        type=Path,
        help="Optional path for the uncompressed gene-annotation intermediate.",
    )
    args = parser.parse_args()

    count = generate_gencode_gene_annotations(
        args.raw_dir,
        args.output,
        debug_bed_path=args.debug_bed,
    )
    print(f"Wrote {count} compressed GENCODE gene annotations")


if __name__ == "__main__":
    main()
