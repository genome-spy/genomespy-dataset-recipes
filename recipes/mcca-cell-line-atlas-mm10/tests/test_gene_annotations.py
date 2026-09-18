# ruff: noqa: E501

import polars as pl
from mcca_genomespy.exon_compression import compress_gene_annotations
from mcca_genomespy.gene_annotations import (
    build_gene_annotations_bed,
    parse_gencode_gtf,
    write_gene_annotation_provenance,
)
from mcca_genomespy.ncbi_gene_tables import filter_taxon_rows


def test_parse_gencode_gtf_builds_gene_exon_rows(tmp_path):
    gtf_path = tmp_path / "gencode.gtf"
    gtf_path.write_text(
        "\n".join(
            [
                "#comment",
                'chr1\tGENCODE\tgene\t101\t250\t.\t+\t.\tgene_id "ENSMUSG0001.1"; gene_name "GeneA"; gene_type "protein_coding";',
                'chr1\tGENCODE\texon\t101\t120\t.\t+\t.\tgene_id "ENSMUSG0001.1"; transcript_id "ENSMUST0001.1"; gene_name "GeneA"; gene_type "protein_coding";',
                'chr1\tGENCODE\texon\t141\t160\t.\t+\t.\tgene_id "ENSMUSG0001.1"; transcript_id "ENSMUST0001.1"; gene_name "GeneA"; gene_type "protein_coding";',
                'chr1_GL456210_random\tGENCODE\tgene\t1\t10\t.\t+\t.\tgene_id "ENSMUSG0002.1"; gene_name "AltGene"; gene_type "protein_coding";',
                'chr1_GL456210_random\tGENCODE\texon\t1\t10\t.\t+\t.\tgene_id "ENSMUSG0002.1"; transcript_id "ENSMUST0002.1"; gene_name "AltGene"; gene_type "protein_coding";',
                'chr1\tGENCODE\tgene\t301\t350\t.\t-\t.\tgene_id "ENSMUSG0003.1"; gene_name "NoPubMed"; gene_type "lncRNA";',
                'chr1\tGENCODE\texon\t301\t350\t.\t-\t.\tgene_id "ENSMUSG0003.1"; transcript_id "ENSMUST0003.1"; gene_name "NoPubMed"; gene_type "lncRNA";',
                "",
            ]
        )
    )

    gencode = parse_gencode_gtf(gtf_path, canonical_chroms={"chr1"})

    assert gencode.to_dicts() == [
        {
            "ensemblGeneId": "ENSMUSG0001",
            "chr": "chr1",
            "txStart": 100,
            "txEnd": 250,
            "geneName": "GeneA",
            "strand": "+",
            "geneType": "protein_coding",
            "exonStarts": "100,140,",
            "exonEnds": "120,160,",
        },
        {
            "ensemblGeneId": "ENSMUSG0003",
            "chr": "chr1",
            "txStart": 300,
            "txEnd": 350,
            "geneName": "NoPubMed",
            "strand": "-",
            "geneType": "lncRNA",
            "exonStarts": "300,",
            "exonEnds": "350,",
        },
    ]


def test_build_gene_annotations_bed_scores_gencode_with_ncbi_pubmed_counts():
    gencode = pl.DataFrame(
        {
            "ensemblGeneId": ["ENSMUSG0001", "ENSMUSG0002"],
            "chr": ["chr1", "chr1"],
            "txStart": [100, 300],
            "txEnd": [250, 350],
            "geneName": ["GeneA", "NoPubMed"],
            "strand": ["+", "-"],
            "geneType": ["protein_coding", "lncRNA"],
            "exonStarts": ["100,140,", "300,"],
            "exonEnds": ["120,160,", "350,"],
        }
    )
    gene2ensembl = pl.DataFrame(
        {
            "GeneID": ["1", "2"],
            "Ensembl_gene_identifier": ["ENSMUSG0001", "ENSMUSG0002"],
        }
    )
    gene2pubmed = pl.DataFrame(
        {
            "GeneID": ["1", "1"],
            "PubMed_ID": ["10", "11"],
        }
    )

    annotations = build_gene_annotations_bed(
        gencode,
        gene2ensembl,
        gene2pubmed,
    )

    assert annotations.to_dicts() == [
        {
            "chr": "chr1",
            "txStart": 100,
            "txEnd": 250,
            "geneName": "GeneA",
            "citationCount": 2,
            "strand": "+",
            "refseqId": "ENSMUSG0001",
            "geneId": "1",
            "geneType": "protein_coding",
            "geneDesc": "",
            "cdsStart": 100,
            "cdsEnd": 250,
            "exonStarts": "100,140,",
            "exonEnds": "120,160,",
        },
        {
            "chr": "chr1",
            "txStart": 300,
            "txEnd": 350,
            "geneName": "NoPubMed",
            "citationCount": 0,
            "strand": "-",
            "refseqId": "ENSMUSG0002",
            "geneId": "2",
            "geneType": "lncRNA",
            "geneDesc": "",
            "cdsStart": 300,
            "cdsEnd": 350,
            "exonStarts": "300,",
            "exonEnds": "350,",
        },
    ]


def test_compress_gene_annotations_merges_overlapping_isoform_exons():
    annotations = pl.DataFrame(
        {
            "chr": ["chr1", "chr1"],
            "txStart": [100, 110],
            "txEnd": [200, 250],
            "geneName": ["GeneA", "GeneA"],
            "citationCount": [2, 2],
            "strand": ["+", "+"],
            "refseqId": ["ENSMUSG0001", "ENSMUSG0001"],
            "geneId": ["ENSMUSG0001", "ENSMUSG0001"],
            "geneType": ["protein-coding", "protein-coding"],
            "geneDesc": ["gene A full name", "gene A full name"],
            "cdsStart": [120, 130],
            "cdsEnd": [180, 240],
            "exonStarts": ["100,140,", "110,170,"],
            "exonEnds": ["120,160,", "130,250,"],
        }
    )

    compressed = compress_gene_annotations(annotations)

    assert compressed.to_dicts() == [
        {
            "symbol": "GeneA",
            "chrom": "chr1",
            "start": 100,
            "length": 150,
            "strand": "+",
            "score": 2,
            "exons": "0,30,10,20,10,80",
        }
    ]


def test_write_gene_annotation_provenance_uses_stable_sidecar_name(tmp_path):
    output_path = tmp_path / "gencodeGenes-mm10.tsv"

    write_gene_annotation_provenance(
        output_path,
        source_filenames=["gencode.vM25.annotation.gtf.gz", "gene2ensembl.gz"],
        row_count=42,
    )

    provenance = (tmp_path / "gencodeGenes-mm10.provenance.txt").read_text()

    assert "Output: gencodeGenes-mm10.tsv" in provenance
    assert "Rows: 42" in provenance
    assert "Annotation: GENCODE mouse M25" in provenance
    assert "gencode.vM25.annotation.gtf.gz" in provenance
    assert "gene2ensembl.gz" in provenance


def test_filter_taxon_rows_keeps_only_requested_taxon_columns():
    rows = [
        ["10090", "1", "mouse", "ignored"],
        ["9606", "2", "human", "ignored"],
        ["10090", "3", "other mouse", "ignored"],
    ]

    filtered = filter_taxon_rows(
        rows,
        columns=["tax_id", "GeneID", "Symbol", "extra"],
        tax_id=10090,
        selected_columns=["GeneID", "Symbol"],
    )

    assert filtered.to_dicts() == [
        {"GeneID": "1", "Symbol": "mouse"},
        {"GeneID": "3", "Symbol": "other mouse"},
    ]
