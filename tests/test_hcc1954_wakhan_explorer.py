"""Sample applicability is required even when another VCF sample has the SV."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "recipes/hcc1954-wakhan-explorer/scripts/prepare.py"
)
spec = importlib.util.spec_from_file_location("wakhan_explorer", SCRIPT)
assert spec and spec.loader
recipe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recipe)


@pytest.mark.parametrize("gt", ["./.", ".|.", ".", "0/0", "0|0", "0", "./1", "1/."])
def test_uncalled_and_reference_genotypes_are_not_variants(gt: str) -> None:
    assert not recipe.has_alt(gt)


@pytest.mark.parametrize("gt", ["0/1", "1|0", "1/1", "2", "0/2", "0/0/1"])
def test_called_alternate_genotypes_are_variants(gt: str) -> None:
    assert recipe.has_alt(gt)


def test_multisample_vcf_uses_target_column(tmp_path: Path) -> None:
    path = tmp_path / "samples.vcf"
    path.write_text(
        "##fileformat=VCFv4.2\n##contig=<ID=chr8,length=145138636>\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tother\twakhan_haplotagged\n"
        "chr8\t100\tother_only\tN\t<DEL>\t.\tPASS\tSVTYPE=DEL;END=200\tGT:DV\t0/1:20\t./.:0\n"
        "chr8\t300\treference\tN\t<DEL>\t.\tPASS\tSVTYPE=DEL;END=400\tGT:DV\t0/1:20\t0/0:0\n"
        "chr8\t500\tapplicable\tN\t<DEL>\t.\tPASS\tSVTYPE=DEL;END=600\tGT:DV\t0/0:0\t0/1:17\n"
        "chr8\t700\tfailed\tN\t<DEL>\t.\tFAIL\tSVTYPE=DEL;END=800\tGT:DV\t0/1:20\t0/1:2\n"
    )
    links, sites, _, counts = recipe.variants(path)
    assert not sites
    assert [r["variantId"] for r in links] == ["applicable"]
    assert links[0]["variantReads"] == "17"
    assert (links[0]["start1"], links[0]["position1"]) == (499, 500)
    assert counts == {
        "sourceRecords": 4,
        "excludedGenotype": 2,
        "excludedFilter": 1,
        "retainedRecords": 1,
    }


def test_target_sample_cannot_be_inferred_from_another_column(tmp_path: Path) -> None:
    path = tmp_path / "wrong-sample.vcf"
    path.write_text("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tother\n")
    with pytest.raises(AssertionError, match="Target sample is missing"):
        recipe.variants(path)


def test_source_svtype_is_preserved_while_wakhan_class_folds_sbnd(
    tmp_path: Path,
) -> None:
    path = tmp_path / "sv-types.vcf"
    path.write_text(
        "##contig=<ID=chr8,length=145138636>\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\twakhan_haplotagged\n"
        "chr8\t100\tsingle\tN\tN.\t.\tPASS\tSVTYPE=sBND\tGT\t0/1\n"
        "chr8\t300\tinversion\tN\t<INV>\t.\tPASS\tSVTYPE=INV;END=400\tGT\t0/1\n"
    )

    links, sites, _, _ = recipe.variants(path)

    assert (links[0]["sourceSvType"], links[0]["svClass"]) == ("INV", "INV")
    assert (sites[0]["sourceSvType"], sites[0]["svClass"]) == ("sBND", "BND")


def test_canonical_driver_support_counts_distinct_publications(tmp_path: Path) -> None:
    path = tmp_path / "ncg.tsv"
    path.write_text(
        "entrez\tsymbol\tpubmed_id\ttype\tNCG_oncogene\tNCG_tsg\n"
        "1\tDRIVER\t11\tCanonical Cancer Driver\t1\t0\n"
        "1\tDRIVER\t11\tWES\t1\t0\n"
        "1\tDRIVER\t22\tWGS\t1\t0\n"
        "2\tCANDIDATE\t33\tWES\t0\t1\n"
    )

    assert recipe.canonical_drivers(path) == {
        "DRIVER": {
            "entrez": 1,
            "ncgClass": "Canonical cancer driver",
            "driverRole": "Oncogene",
            "supportCount": 2,
        }
    }


def test_loh_regions_preserve_source_calls_but_omit_masked_parts(
    tmp_path: Path,
) -> None:
    path = tmp_path / "loh.bed"
    path.write_text("#chr\tstart\tend\nchr8\t100\t500\nchr8\t700\t900\n")
    masked = [
        {"chrom": "chr8", "start": 200, "end": 300},
        {"chrom": "chr8", "start": 400, "end": 800},
    ]

    rows, validation = recipe.loh_regions(path, {"chr8": 1000}, masked)

    assert [(row["start"], row["end"]) for row in rows] == [
        (100, 200),
        (300, 400),
        (800, 900),
    ]
    assert [(row["sourceStart"], row["sourceEnd"]) for row in rows] == [
        (100, 500),
        (100, 500),
        (700, 900),
    ]
    assert validation == {
        "sourceIntervals": 2,
        "displayedIntervals": 3,
        "sourceBases": 600,
        "displayedBases": 300,
        "maskedOverlapBases": 300,
        "policy": "Use Wakhan LOH calls, excluding source depth-mask overlap",
    }


def test_copy_number_masks_omit_placeholders_but_keep_biological_zero() -> None:
    source = [
        {
            "chrom": "chr8",
            "start": 100,
            "end": 200,
            "haplotype": "HP1",
            "copyNumber": 0,
            "medianCoverage": 0,
        },
        {
            "chrom": "chr8",
            "start": 100,
            "end": 200,
            "haplotype": "HP2",
            "copyNumber": 0,
            "medianCoverage": 0,
        },
        {
            "chrom": "chr8",
            "start": 300,
            "end": 400,
            "haplotype": "HP1",
            "copyNumber": 0,
            "medianCoverage": 0,
        },
    ]
    masked = [{"chrom": "chr8", "start": 100, "end": 200}]

    rows, validation = recipe.omit_masked_copy_number_segments(source, masked)

    assert rows == [source[2]]
    assert validation == {
        "sourceIntervals": 3,
        "displayedIntervals": 1,
        "maskedPlaceholdersOmitted": 2,
        "policy": "Omit exact mask-matching CN-zero placeholders",
    }


@pytest.mark.parametrize("mate_gt", ["0/1", "./."])
def test_bnd_pair_requires_two_applicable_mates(tmp_path: Path, mate_gt: str) -> None:
    path = tmp_path / "paired.vcf"
    path.write_text(
        "##contig=<ID=chr8,length=145138636>\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\twakhan_haplotagged\n"
        "chr8\t100\ta\tN\tN[chr8:200[\t.\tPASS\tSVTYPE=BND;MATE_ID=b\tGT\t0/1\n"
        f"chr8\t200\tb\tN\t]chr8:100]N\t.\tPASS\tSVTYPE=BND;MATE_ID=a\tGT\t{mate_gt}\n"
    )
    if mate_gt == "./.":
        with pytest.raises(AssertionError, match="Missing or filtered BND mate"):
            recipe.variants(path)
    else:
        links, sites, _, _ = recipe.variants(path)
        assert not sites and len(links) == 1
        assert (links[0]["variantId"], links[0]["mateId"]) == ("a", "b")
        assert (links[0]["position1"], links[0]["position2"]) == (100, 200)
