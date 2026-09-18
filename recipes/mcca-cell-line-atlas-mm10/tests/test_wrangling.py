# ruff: noqa: E501

import gzip
import math
import zipfile

import mcca_genomespy.expression as expression
import mcca_genomespy.values as values
import mcca_genomespy.wrangle as wrangle
import pyarrow.parquet as pq
import zarr
from mcca_genomespy.expression import (
    GeneInfo,
    load_gencode_gene_map,
    parse_expression_float,
    write_transcriptome_zarr,
)
from mcca_genomespy.sequencing_metadata import (
    extract_mcca_id,
    read_run_report_sample_ids,
    sequencing_metadata_rows,
    sequencing_type,
    write_sequencing_metadata_parquet,
)
from mcca_genomespy.wrangle import (
    CANONICAL_CHROMS,
    CNV_SCHEMA,
    METADATA_SCHEMA,
    MODEL_ALLELE_SAMPLE_ID_FIELD,
    MUTATION_SCHEMA,
    clean_text,
    model_allele_rows,
    normalize_chrom,
    normalize_cnv_row,
    normalize_metadata_row,
    normalize_mutation_row,
    parse_model_alleles,
    write_metadata_parquet,
    write_model_alleles_parquet,
    write_parquet,
)


def test_expression_helpers_live_in_expression_module():
    assert expression.GeneInfo is GeneInfo
    assert expression.write_transcriptome_zarr is write_transcriptome_zarr


def test_missing_value_policy_is_shared():
    assert wrangle.is_missing_value is values.is_missing_value
    assert expression.is_missing_value is values.is_missing_value


def test_normalize_chrom_keeps_only_canonical_mm10_chromosomes():
    assert normalize_chrom("1") == "chr1"
    assert normalize_chrom("1.0") == "chr1"
    assert normalize_chrom("X") == "chrX"
    assert normalize_chrom("chrY") == "chrY"
    assert normalize_chrom("GL455991.1") is None
    assert normalize_chrom("AY172335.1") is None
    assert normalize_chrom("MT") is None
    assert CANONICAL_CHROMS[-2:] == ("chrX", "chrY")


def test_missing_value_tokens_are_normalized():
    assert clean_text(None) == ""
    assert clean_text("NA") == ""
    assert clean_text("NaN") == ""
    assert clean_text(" n/a ") == ""
    assert clean_text("real value") == "real value"
    assert math.isnan(parse_expression_float("NA"))


def test_normalize_cnv_row_renames_fields_and_drops_alt_contigs():
    row = {
        "MCCA_ID": "MCCA0001",
        "CHROM": "2.0",
        "START-mm10": "100",
        "END-mm10": "200",
        "LOG2FC": "0.5",
    }

    assert normalize_cnv_row(row) == {
        "sample": "MCCA0001",
        "chrom": "chr2",
        "start": 100,
        "end": 200,
        "log2fc": 0.5,
    }

    row["CHROM"] = "GL455991.1"
    assert normalize_cnv_row(row) is None


def test_normalize_metadata_row_preserves_source_column_names():
    row = {
        "MCCA-ID": "MCCA0001",
        "CellLineName": "MCCA-1",
        "MouseID": "Mouse-1",
        "TumorLocation": "pancreas",
        "CellLineSource": "primary",
        "CellLineDistributor": "MCCA",
        "PublicationStatus": "published",
        "MouseModelType": "GEMM",
        "MouseModel": "Kras",
        "MouseModelDetailed": "KrasG12D",
        "Tissue": "Pancreas",
        "Lineage": "Pancreas",
        "Site": "Primary",
        "CancerType": "PDAC",
        "CancerTypeDetailed": "Pancreatic ductal adenocarcinoma",
        "MicroscopicMorphology": "epithelial",
        "MicroscopicMorphologyDetailed": "ductal",
        "SurvivalDays": "NaN",
        "DistantMetastasis": "NA",
        "ComplexRearrangement": "No",
        "Chromothripsis": "No",
        "Gender": "Female",
        "ImmunocompetentTransplantation": "Yes",
    }

    normalized = normalize_metadata_row(row)

    assert "cell_line_name" not in normalized
    assert normalized["MCCA-ID"] == "MCCA0001"
    assert normalized["CellLineName"] == "MCCA-1"
    assert normalized["CancerTypeDetailed"] == "Pancreatic ductal adenocarcinoma"
    assert normalized["SurvivalDays"] is None
    assert normalized["DistantMetastasis"] is None


def test_write_metadata_parquet_preserves_types_and_nulls(tmp_path):
    output_path = tmp_path / "samples.parquet"
    rows = [
        {column: "value" for column in METADATA_SCHEMA},
        {column: None for column in METADATA_SCHEMA},
    ]
    rows[0]["MCCA-ID"] = "MCCA0001"
    rows[0]["SurvivalDays"] = 101
    rows[1]["MCCA-ID"] = "MCCA0002"

    count = write_metadata_parquet(output_path, rows)
    table = pq.read_table(output_path)

    assert count == 2
    assert table.num_rows == 2
    assert table.column_names == list(METADATA_SCHEMA)
    assert table.schema.field("SurvivalDays").type.bit_width == 32
    assert table.column("CellLineName").null_count == 1
    assert table.column("SurvivalDays").null_count == 1


def test_write_parquet_preserves_mcca_derived_table_schema(tmp_path):
    copy_ratio_path = tmp_path / "copy-ratios.parquet"
    mutation_path = tmp_path / "mutations.parquet"

    copy_ratio_count = write_parquet(
        copy_ratio_path,
        CNV_SCHEMA,
        [
            {
                "sample": "MCCA0001",
                "chrom": "chr1",
                "start": 1,
                "end": 10,
                "log2fc": 0.5,
            },
        ],
    )
    mutation_count = write_parquet(
        mutation_path,
        MUTATION_SCHEMA,
        [
            {
                "sample": "MCCA0001",
                "chrom": "chr1",
                "pos": 5,
                "ref": "A",
                "alt": "T",
                "tumor_af": 0.25,
                "tumor_ref_depth": None,
                "tumor_alt_depth": 12,
                "normal_ref_depth": None,
                "normal_alt_depth": 0,
                "gene": "Kras",
                "effect": "missense_variant",
                "impact": "MODERATE",
                "feature_id": "ENSMUST00000000001",
                "hgvs_c": "",
                "hgvs_p": "p.Gly12Asp",
                "normal_ngs": "",
            },
        ],
    )

    copy_ratio_table = pq.read_table(copy_ratio_path)
    mutation_table = pq.read_table(mutation_path)

    assert copy_ratio_count == 1
    assert mutation_count == 1
    assert copy_ratio_table.column_names == list(CNV_SCHEMA)
    assert mutation_table.column_names == list(MUTATION_SCHEMA)
    assert copy_ratio_table.schema.field("start").type.bit_width == 32
    assert mutation_table.schema.field("tumor_ref_depth").type.bit_width == 32
    assert mutation_table.column("tumor_ref_depth").null_count == 1


def test_parse_model_alleles_extracts_gene_allele_components():
    alleles = parse_model_alleles(
        "Alb-Cre;Kras,LSL-G12D/+;Trp53,LSL-R172H/+;Cdkn2a,FL/FL;"
        "Irradiation,G;rAAV8-sgPten;Wt"
    )

    assert alleles == {
        "Kras": "LSL-G12D/+",
        "Trp53": "LSL-R172H/+",
        "Cdkn2a": "FL/FL",
    }


def test_parse_model_alleles_joins_multiple_alleles_for_the_same_gene():
    alleles = parse_model_alleles("Kras,LSL-G12D/+;Kras,FSF-G12C/+")

    assert alleles == {
        "Kras": "LSL-G12D/+;FSF-G12C/+",
    }


def test_write_model_alleles_parquet_uses_dynamic_gene_columns(tmp_path):
    output_path = tmp_path / "model-alleles.parquet"
    metadata_rows = [
        {
            "MCCA-ID": "MCCA0001",
            "MouseModelDetailed": "Alb-Cre;Kras,LSL-G12D/+;Trp53,FL/FL",
        },
        {
            "MCCA-ID": "MCCA0002",
            "MouseModelDetailed": "Braf,LSL-V600E/+",
        },
    ]

    count = write_model_alleles_parquet(
        output_path,
        model_allele_rows(metadata_rows),
    )
    table = pq.read_table(output_path)

    assert count == 2
    assert table.column_names == [
        MODEL_ALLELE_SAMPLE_ID_FIELD,
        "Braf",
        "Kras",
        "Trp53",
    ]
    assert table.to_pylist() == [
        {
            "MCCA-ID": "MCCA0001",
            "Braf": None,
            "Kras": "LSL-G12D/+",
            "Trp53": "FL/FL",
        },
        {
            "MCCA-ID": "MCCA0002",
            "Braf": "LSL-V600E/+",
            "Kras": None,
            "Trp53": None,
        },
    ]


def test_sequencing_metadata_derives_assay_availability_from_ena_aliases(tmp_path):
    lcwgs_path = tmp_path / "lcwgs.tsv"
    wes_path = tmp_path / "wes.tsv"
    lcwgs_path.write_text(
        "run_accession\tsample_alias\n"
        "ERR1\tMCCA0001-Cells-lcWGS\n"
        "ERR2\tMCCA0002-Cells-lcWGS\n"
    )
    wes_path.write_text(
        "run_accession\tsample_alias\nERR3\tMCCA0002-Cells\nERR4\tMCCA0003-Cells\n"
    )
    sample_rows = [
        {"MCCA-ID": "MCCA0001"},
        {"MCCA-ID": "MCCA0002"},
        {"MCCA-ID": "MCCA0003"},
        {"MCCA-ID": "MCCA0004"},
    ]

    rows = list(
        sequencing_metadata_rows(
            sample_rows,
            read_run_report_sample_ids(lcwgs_path),
            read_run_report_sample_ids(wes_path),
        )
    )

    assert extract_mcca_id("MCCA0506-Cells-lcWGS") == "MCCA0506"
    assert sequencing_type(True, True) == "lcWGS+WES"
    assert rows == [
        {"MCCA-ID": "MCCA0001", "SequencingAvailability": "lcWGS only"},
        {"MCCA-ID": "MCCA0002", "SequencingAvailability": "lcWGS+WES"},
        {"MCCA-ID": "MCCA0003", "SequencingAvailability": "WES only"},
        {"MCCA-ID": "MCCA0004", "SequencingAvailability": None},
    ]


def test_write_sequencing_metadata_parquet_uses_mcca_id_and_nominal_type(tmp_path):
    output_path = tmp_path / "sequencing.parquet"

    count = write_sequencing_metadata_parquet(
        output_path,
        [
            {"MCCA-ID": "MCCA0001", "SequencingAvailability": "lcWGS only"},
            {"MCCA-ID": "MCCA0002", "SequencingAvailability": None},
        ],
    )
    table = pq.read_table(output_path)

    assert count == 2
    assert table.column_names == ["MCCA-ID", "SequencingAvailability"]
    assert (
        table.schema.field("MCCA-ID").type
        == table.schema.field("SequencingAvailability").type
    )
    assert table.column("SequencingAvailability").null_count == 1


def test_load_gencode_gene_map_reads_gene_symbols(tmp_path):
    gtf_path = tmp_path / "gencode.gtf.gz"
    content = (
        "chr1\tHAVANA\tgene\t10\t20\t.\t+\t.\t"
        'gene_id "ENSMUSG00000000001.1"; gene_type "protein_coding"; gene_name "GeneA";\n'
        "chr1\tHAVANA\ttranscript\t10\t20\t.\t+\t.\t"
        'gene_id "ENSMUSG00000000001.1"; transcript_id "ENSMUST00000000001.1"; gene_name "GeneA";\n'
    )
    with gzip.open(gtf_path, "wt") as file:
        file.write(content)

    gene_map = load_gencode_gene_map(gtf_path)

    assert gene_map["ENSMUSG00000000001"].symbol == "GeneA"
    assert gene_map["ENSMUSG00000000001"].gene_type == "protein_coding"


def test_write_transcriptome_zarr_uses_symbols_as_primary_column_ids(tmp_path):
    zip_path = tmp_path / "expression.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "expression.tsv",
            "Gene\tMCCA0001\tMCCA0002\n"
            "ENSMUSG00000000001\t1.0\t3.0\n"
            "ENSMUSG00000000002\t4.0\t4.0\n",
        )

    output_dir = tmp_path / "expression.zarr"

    write_transcriptome_zarr(
        zip_path,
        output_dir,
        gene_map={
            "ENSMUSG00000000001": GeneInfo("GeneA", "protein_coding"),
            "ENSMUSG00000000002": GeneInfo("GeneB", "protein_coding"),
        },
        row_chunk_size=2,
        column_chunk_size=2,
    )

    root = read_zarr(output_dir)

    assert root["var_names"][:].tolist() == ["GeneA", "GeneB"]
    assert root["var"]["symbol"][:].tolist() == ["GeneA", "GeneB"]
    assert root["var"]["ensembl_id"][:].tolist() == [
        "ENSMUSG00000000001",
        "ENSMUSG00000000002",
    ]
    assert root["var"]["gene_type"][:].tolist() == [
        "protein_coding",
        "protein_coding",
    ]


def test_write_transcriptome_zarr_rejects_duplicate_symbols(tmp_path):
    zip_path = tmp_path / "expression.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "expression.tsv",
            "Gene\tMCCA0001\nENSMUSG00000000001\t1.0\nENSMUSG00000000002\t2.0\n",
        )

    gene_info = GeneInfo("Shared", "protein_coding")

    try:
        write_transcriptome_zarr(
            zip_path,
            tmp_path / "expression.zarr",
            gene_map={
                "ENSMUSG00000000001": gene_info,
                "ENSMUSG00000000002": gene_info,
            },
        )
    except ValueError as error:
        assert str(error) == "Duplicate transcriptome gene symbol: Shared"
    else:
        raise AssertionError("Expected duplicate gene symbol to fail")


def test_normalize_mutation_row_renames_fields_and_preserves_context():
    row = {
        "MCCA_ID": "MCCA0027",
        "CHROM": "10.0",
        "POS-mm10": "4493222.0",
        "REF": "G",
        "ALT": "C",
        "GEN[Tumor].AF": "0.4",
        "GEN[Tumor].AD[0]": "22.0",
        "GEN[Tumor].AD[1]": "17.0",
        "GEN[Normal].AD[0]": "92.0",
        "GEN[Normal].AD[1]": "0.0",
        "ANN[*].GENE": "Sox17",
        "ANN[*].EFFECT": "missense_variant",
        "ANN[*].IMPACT": "MODERATE",
        "ANN[*].FEATUREID": "ENSMUST00000027035",
        "ANN[*].HGVS_C": "c.1G>C",
        "ANN[*].HGVS_P": "p.Met1Ile",
        "NORMAL_NGS": "Yes",
    }

    assert normalize_mutation_row(row) == {
        "sample": "MCCA0027",
        "chrom": "chr10",
        "pos": 4493222,
        "ref": "G",
        "alt": "C",
        "tumor_af": 0.4,
        "tumor_ref_depth": 22,
        "tumor_alt_depth": 17,
        "normal_ref_depth": 92,
        "normal_alt_depth": 0,
        "gene": "Sox17",
        "effect": "missense_variant",
        "impact": "MODERATE",
        "feature_id": "ENSMUST00000027035",
        "hgvs_c": "c.1G>C",
        "hgvs_p": "p.Met1Ile",
        "normal_ngs": "Yes",
    }

    row["CHROM"] = "JH584295.1"
    assert normalize_mutation_row(row) is None


def test_normalize_mutation_row_allows_missing_optional_depths():
    row = {
        "MCCA_ID": "MCCA0027",
        "CHROM": "X",
        "POS-mm10": "101",
        "REF": "A",
        "ALT": "T",
        "GEN[Tumor].AF": "0.25",
        "GEN[Tumor].AD[0]": None,
        "GEN[Tumor].AD[1]": "",
        "GEN[Normal].AD[0]": None,
        "GEN[Normal].AD[1]": "",
        "ANN[*].GENE": "Kras",
        "ANN[*].EFFECT": "missense_variant",
        "ANN[*].IMPACT": "MODERATE",
        "ANN[*].FEATUREID": "",
        "ANN[*].HGVS_C": "",
        "ANN[*].HGVS_P": "p.Gly12Asp",
        "NORMAL_NGS": "",
    }

    normalized = normalize_mutation_row(row)

    assert normalized["tumor_ref_depth"] is None
    assert normalized["tumor_alt_depth"] is None
    assert normalized["normal_ref_depth"] is None
    assert normalized["normal_alt_depth"] is None


def test_write_transcriptome_zarr_transposes_gene_by_sample_table(tmp_path):
    zip_path = tmp_path / "expression.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "expression.tsv",
            "Gene\tMCCA0002\tMCCA0001\n"
            "ENSMUSG00000000001\t1.5\t2.5\n"
            "ENSMUSG00000000002\t3.5\t4.5\n",
        )

    output_dir = tmp_path / "expression.zarr"

    summary = write_transcriptome_zarr(
        zip_path, output_dir, row_chunk_size=2, column_chunk_size=2
    )

    assert summary == {
        "samples": 2,
        "genes": 2,
        "matrix_cells": 4,
    }
    root = read_zarr(output_dir)

    assert root["X"].shape == (2, 2)
    assert root["X"].chunks == (2, 2)
    assert root["obs_names"][:].tolist() == ["MCCA0002", "MCCA0001"]
    assert root["var_names"][:].tolist() == [
        "ENSMUSG00000000001",
        "ENSMUSG00000000002",
    ]
    assert root["X"][:].reshape(-1).tolist() == [-1.0, -1.0, 1.0, 1.0]


def test_write_transcriptome_zarr_maps_zero_variance_genes_to_zero(tmp_path):
    zip_path = tmp_path / "expression.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "expression.tsv",
            "Gene\tMCCA0001\tMCCA0002\nENSMUSG00000000001\t2.0\t2.0\n",
        )

    output_dir = tmp_path / "expression.zarr"

    write_transcriptome_zarr(
        zip_path, output_dir, row_chunk_size=2, column_chunk_size=2
    )

    assert read_zarr(output_dir)["X"][:].reshape(-1).tolist() == [0.0, 0.0]


def test_write_transcriptome_zarr_preserves_missing_expression_values(tmp_path):
    zip_path = tmp_path / "expression.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "expression.tsv",
            "Gene\tMCCA0001\tMCCA0002\tMCCA0003\nENSMUSG00000000001\t1.0\tNA\t3.0\n",
        )

    output_dir = tmp_path / "expression.zarr"

    write_transcriptome_zarr(
        zip_path, output_dir, row_chunk_size=3, column_chunk_size=1
    )

    values = read_zarr(output_dir)["X"][:].reshape(-1).tolist()
    assert values[0] == -1.0
    assert math.isnan(values[1])
    assert values[2] == 1.0


def test_write_transcriptome_zarr_rejects_duplicate_genes(tmp_path):
    zip_path = tmp_path / "expression.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "expression.tsv",
            "Gene\tMCCA0001\nENSMUSG00000000001\t1.5\nENSMUSG00000000001\t2.5\n",
        )

    try:
        write_transcriptome_zarr(zip_path, tmp_path / "expression.zarr")
    except ValueError as error:
        assert str(error) == "Duplicate transcriptome gene id: ENSMUSG00000000001"
    else:
        raise AssertionError("Expected duplicate gene id to fail")


def read_zarr(path):
    return zarr.open_group(
        store=zarr.storage.LocalStore(path),
        mode="r",
    )
