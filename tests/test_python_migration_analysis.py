"""Small scientific-contract checks for independent migration preparation."""

from __future__ import annotations

import gzip
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "recipes"


def module(recipe: str, filename: str = "prepare.py"):
    path = ROOT / recipe / "scripts" / filename
    spec = importlib.util.spec_from_file_location(recipe, path)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def transcript(start, end, symbol="GENE", strand="+", chrom="chr1"):
    return "\t".join(
        map(
            str,
            [
                0,
                f"NM_{start}",
                chrom,
                strand,
                start,
                end,
                start,
                end,
                1,
                f"{start},",
                f"{end},",
                0,
                symbol,
                "cmpl",
                "cmpl",
                "0,",
            ],
        )
    )


def test_refseq_merges_touching_intervals_but_preserves_locus_boundaries():
    recipe = module("ucsc-refseq-gene-bodies")
    rows = [
        transcript(10, 20),
        transcript(20, 30),
        transcript(12, 17),
        transcript(40, 50),
        transcript(10, 20, strand="-"),
        transcript(10, 20, symbol="OTHER"),
        transcript(10, 20, chrom="chr1_alt"),
    ]
    result = recipe.gene_bodies(
        gzip.compress(("\n".join(rows) + "\n").encode()), "hg19"
    )
    same = [r for r in result if r["symbol"] == "GENE" and r["strand"] == "+"]
    assert [(r["start"], r["end"], r["score"]) for r in same] == [
        (10, 30, 3),
        (40, 50, 1),
    ]
    assert len(result) == 4
    assert same[0]["identifier"] == "GENE:chr1:10-30:+"
    assert {r["assembly"] for r in result} == {"hg19"}


def test_airway_adjusts_full_test_universe_before_display_selection():
    review = module("bioconnector-airway-rnaseq", "review.py")
    metadata = "id,dex,celltype,geo_id\n" + "".join(
        f"S{i},{'control' if i % 2 == 0 else 'treated'},C{i // 2},G{i}\n"
        for i in range(8)
    )
    counts = "ensgene," + ",".join(f"S{i}" for i in range(8)) + "\n"
    counts += "ENSG1,15,31,15,63,15,127,15,255\n"  # Log2 differences 1,2,3,4.
    counts += "ENSG2,12,12,12,12,12,12,12,12\n"  # Null effect: p=1.
    counts += "ENSG3,15,31,15,31,15,31,15,31\n"  # Constant effect: p=0.
    params = {
        "minimumMean": 10,
        "maximumGenes": 1,
        "effectCutoff": 1,
        "pvalueCutoff": 0.05,
        "fdrAlpha": 0.1,
        "geneSymbols": {"ENSG1": "LABEL"},
        "volcanoLabels": ["LABEL"],
        "maLabels": [],
        "bundleProvenance": {},
    }
    with pytest.warns(RuntimeWarning, match="Precision loss"):
        result = json.loads(
            gzip.decompress(
                review.prepare_review(
                    {"metadata": metadata.encode(), "counts": counts.encode()}, params
                )
            )
        )
    assert len(result["genes"]) == 1
    gene = result["genes"][0]
    assert gene["ensgene"] == "ENSG1"
    assert gene["log2fc"] == 2.5
    assert gene["pvalue"] == pytest.approx(0.030466291662170977)
    assert gene["padj"] == pytest.approx(0.045699437493256464)
    assert gene["volcano_label"] == "LABEL"
    assert gene["ma_label"] is None
    assert gene["S0"] == 15
    assert gene["direction"] == "up in dex"


def test_laml_input_manifest_pins_all_six_required_inputs():
    p = ROOT / "maftools-tcga-laml-oncoplot" / "provenance.json"
    record = json.loads(p.read_text())
    identities = record["parameters"]["bundleProvenance"]["sha256"]
    assert len(record["sources"]) == 6
    assert {s["filename"]: s["sha256"] for s in record["sources"]} == identities
    assert set(identities) == {
        "tcga_laml.maf.gz",
        "tcga_laml_annot.tsv",
        "all_lesions.conf_99.txt",
        "amp_genes.conf_99.txt",
        "del_genes.conf_99.txt",
        "LAML_sig_genes.txt.gz",
    }


def test_laml_combines_hits_cnv_burden_and_synonymous_spectrum():
    recipe = module("maftools-tcga-laml-oncoplot")
    first, second = "TCGA-AB-0001", "TCGA-AB-0002"
    maf = (
        "Tumor_Sample_Barcode\tHugo_Symbol\tVariant_Classification\tTumor_Seq_Allele2"
        "\ti_TumorVAF_WU\tVariant_Type\tReference_Allele\n"
        f"{first}\tG1\tMissense_Mutation\tC\t20\tSNP\tA\n"
        f"{first}\tG1\tMissense_Mutation\tT\t40\tSNP\tC\n"
        f"{second}\tG1\tSilent\tG\t10\tSNP\tA\n"
    )
    clinical = f"Tumor_Sample_Barcode\tFAB_classification\n{first}\tM0\n{second}\tM0\n"
    lesions = (
        "\t".join(
            [
                "Unique Name",
                "Descriptor",
                "Wide Peak Limits",
                *[f"extra{i}" for i in range(6)],
                first,
                second,
            ]
        )
        + "\n"
    )
    lesions += (
        "\t".join(
            [
                "Amplification Peak 1",
                "1p",
                "chr1:10-20(probes 1:2)",
                *["0"] * 6,
                "0",
                "1",
            ]
        )
        + "\n"
    )
    sources = {
        "tcga_laml.maf.gz": gzip.compress(maf.encode()),
        "tcga_laml_annot.tsv": clinical.encode(),
        "all_lesions.conf_99.txt": lesions.encode(),
        "amp_genes.conf_99.txt": (
            b"cytoband\t1p\nq\t0.01\nresidual\t0.01\nbounds\tchr1:10-20\ngene\tG1\n"
        ),
        "del_genes.conf_99.txt": b"cytoband\nq\nresidual\nbounds\n",
        "LAML_sig_genes.txt.gz": gzip.compress(b"gene\tq\nG1\t0.01\n"),
    }
    result = recipe.bundle(
        sources,
        {
            "pathways": {"Path": ["G1"]},
            "nonsynonymousClasses": ["Missense_Mutation"],
            "sampleIdLength": 12,
            "bundleProvenance": {},
        },
    )
    assert len(result["events"]) == 1
    assert result["events"][0]["class"] == "Multi_Hit"
    assert result["events"][0]["alt_c"] is True
    assert result["copy_number"][0]["sample"] == second
    assert result["copy_number"][0]["class"] == "Amp"
    assert result["genes"][0]["vaf"] == 30
    assert result["genes"][0]["neglog_q"] == 2
    assert result["genes"][0]["altered_percent"] == 100
    assert [(r["sample"], r["count"]) for r in result["burden"]] == [
        (first, 2),
        (second, 1),
    ]
    assert result["burden_limit"] == 2
    assert [r for r in result["spectrum"] if r["sample"] == second] == [
        {"sample": second, "sample_order": 1, "substitution": "T>C", "percent": 100}
    ]
    assert result["altered_samples"] == 2
