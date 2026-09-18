import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads((ROOT / path).read_text())


def test_metadata_source_uses_preserved_mcca_id_for_sample_matching():
    spec = read_json("specs/spec.json")
    metadata = read_json("specs/metadata.json")

    identity = spec["vconcat"][1]["samples"]["identity"]
    backend = metadata["backend"]

    assert identity["idField"] == "MCCA-ID"
    assert identity["data"]["url"] == "../output/processed/samples.parquet"
    assert identity["data"]["format"]["type"] == "parquet"
    assert backend["sampleIdField"] == "MCCA-ID"
    assert backend["data"]["url"] == "../output/processed/samples.parquet"
    assert backend["data"]["format"]["type"] == "parquet"
    assert "parse" not in backend["data"]["format"]


def test_model_allele_metadata_source_uses_parquet_and_mcca_id():
    spec = read_json("specs/spec.json")
    model_alleles = read_json("specs/model-alleles.json")

    source_urls = [
        source["import"]["url"] for source in spec["vconcat"][1]["metadata"]["sources"]
    ]
    backend = model_alleles["backend"]

    assert "model-alleles.json" in source_urls
    assert backend["sampleIdField"] == "MCCA-ID"
    assert backend["data"]["url"] == "../output/processed/model-alleles.parquet"
    assert backend["data"]["format"]["type"] == "parquet"
    assert model_alleles["attributes"][""] == {
        "visible": False,
        "type": "nominal",
    }


def test_sequencing_metadata_source_uses_parquet_and_describes_availability():
    spec = read_json("specs/spec.json")
    sequencing = read_json("specs/sequencing.json")

    source_urls = [
        source["import"]["url"] for source in spec["vconcat"][1]["metadata"]["sources"]
    ]
    backend = sequencing["backend"]
    attribute = sequencing["attributes"]["SequencingAvailability"]

    assert "sequencing.json" in source_urls
    assert backend["sampleIdField"] == "MCCA-ID"
    assert backend["data"]["url"] == "../output/processed/sequencing.parquet"
    assert backend["data"]["format"]["type"] == "parquet"
    assert attribute["type"] == "nominal"
    assert "lcWGS only" in attribute["description"]
    assert "WES only" in attribute["description"]
    assert (
        "not which assay produced the displayed copy-ratio profile"
        in attribute["description"]
    )


def test_transcriptome_source_uses_symbol_primary_and_ensembl_lookup():
    transcriptome = read_json("specs/transcriptome.json")

    identifiers = transcriptome["backend"]["identifiers"]

    assert (
        "Ensembl mouse gene IDs retained as lookup identifiers"
        in transcriptome["description"]
    )
    assert transcriptome["backend"]["url"] == "../output/processed/expression.zarr"
    assert identifiers == [
        {
            "name": "symbol",
            "path": "var/symbol",
            "primary": True,
            "caseInsensitive": True,
        },
        {
            "name": "ensembl",
            "path": "var/ensembl_id",
            "stripVersionSuffix": True,
        },
    ]


def test_mcca_derived_track_data_uses_parquet():
    copy_ratios = read_json("specs/copy-ratios.json")
    mutations = read_json("specs/mutations.json")

    assert copy_ratios["data"]["url"] == "../output/processed/copy-ratios.parquet"
    assert copy_ratios["data"]["format"] == {"type": "parquet"}
    assert mutations["data"]["url"] == "../output/processed/mutations.parquet"
    assert mutations["data"]["format"] == {"type": "parquet"}


def test_gene_annotation_track_uses_gencode_output():
    spec = read_json("specs/spec.json")
    genes = read_json("specs/gencode-genes.json")

    assert spec["vconcat"][2]["import"]["url"] == "gencode-genes.json"
    assert genes["data"]["url"] == "../output/external-data/gencodeGenes-mm10.tsv"
    assert "GENCODE mouse M25" in genes["description"]
    assert genes["layer"][1]["layer"][0]["mark"]["tooltip"] == {
        "handler": "refseqgene",
        "params": {
            "Organism": "Mus musculus",
        },
    }
