"""Check input identity and scientific contracts without external network access."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECIPES = ("manhattanly-hapmap-associations", "bioconnector-airway-rnaseq")


def load_recipe(name: str) -> ModuleType:
    """Load an independent recipe entrypoint for isolated tests."""
    path = ROOT / "recipes" / name / "scripts" / "prepare.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("recipe", RECIPES)
def test_corrupt_cached_input_is_rejected_without_network(
    recipe, tmp_path, monkeypatch
):
    module = load_recipe(recipe)
    original = b"accepted"
    record = {
        "filename": "source.txt",
        "url": "https://example.invalid/source.txt",
        "fileSizeBytes": len(original),
        "sha256": hashlib.sha256(original).hexdigest(),
    }
    (tmp_path / "source.txt").write_bytes(b"tampered")

    def unexpected_network(*args, **kwargs):
        pytest.fail("A corrupt existing source must not trigger a replacement download")

    monkeypatch.setattr(module, "urlopen", unexpected_network)
    with pytest.raises(ValueError, match="SHA-256"):
        module.read_source(record, tmp_path)
    assert (tmp_path / "source.txt").read_bytes() == b"tampered"


@pytest.mark.parametrize("recipe", RECIPES)
def test_truncated_input_is_rejected(recipe):
    module = load_recipe(recipe)
    with pytest.raises(ValueError, match="byte size"):
        module.verify(b"short", {"fileSizeBytes": 10, "sha256": "unused"}, "input")


@pytest.mark.parametrize("recipe", RECIPES)
def test_verify_only_never_downloads_or_rewrites(recipe, tmp_path, monkeypatch):
    module = load_recipe(recipe)
    output = tmp_path / "output.txt"
    output.write_bytes(b"unchanged")
    provenance = {
        "outputs": {
            "table": {
                "path": "output.txt",
                "fileSizeBytes": 9,
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            }
        },
        "validation": {},
    }
    (tmp_path / "provenance.json").write_text(json.dumps(provenance))
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr("sys.argv", ["prepare.py", "--verify-only"])
    calls = []
    monkeypatch.setattr(module, "validate_tables", lambda *args: calls.append(args))

    def forbidden(*args, **kwargs):
        pytest.fail("verify-only must not fetch or write")

    monkeypatch.setattr(module, "read_source", forbidden)
    monkeypatch.setattr(module, "write_atomic", forbidden)
    module.main()
    assert calls == [({"table": b"unchanged"}, {})]
    output.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="SHA-256"):
        module.main()


HAPMAP_HEADER = "CHR,BP,P,SNP,ZSCORE,EFFECTSIZE,GENE,DISTANCE\n"


def test_hapmap_keeps_historical_affymetrix_identifiers():
    module = load_recipe(RECIPES[0])
    raw = (
        HAPMAP_HEADER + "1,123,0.1,AFFX-SNP_9826961__rs17120034,1.2,-0.1,GENE,1\n"
    ).encode()
    module.validate_tables(
        {"associations": raw},
        {"columns": HAPMAP_HEADER.strip().split(","), "recordCount": 1},
    )


@pytest.mark.parametrize(
    "row",
    [
        "1,123,nan,rs1,1.2,-0.1,GENE,1",
        "1,123,0,rs1,1.2,-0.1,GENE,1",
        "1,123,0.1,rs1,inf,-0.1,GENE,1",
        "24,123,0.1,rs1,1.2,-0.1,GENE,1",
        "1,0,0.1,rs1,1.2,-0.1,GENE,1",
    ],
)
def test_hapmap_rejects_invalid_scientific_values(row):
    module = load_recipe(RECIPES[0])
    with pytest.raises(ValueError):
        module.validate_tables(
            {"associations": (HAPMAP_HEADER + row + "\n").encode()},
            {"columns": HAPMAP_HEADER.strip().split(","), "recordCount": 1},
        )


def airway_fixture():
    metadata = "id,dex,celltype,geo_id\n" + "".join(
        f"S{i},{'control' if i % 2 == 0 else 'treated'},C{i // 2},G{i}\n"
        for i in range(8)
    )
    counts = "ensgene," + ",".join(f"S{i}" for i in range(8)) + "\n"
    counts += "ENSG1," + ",".join("1.0" for _ in range(8)) + "\n"
    return {"metadata": metadata.encode(), "counts": counts.encode()}


@pytest.mark.parametrize("problem", ["pair", "column", "negative", "fractional", "nan"])
def test_airway_rejects_broken_sample_or_count_contract(problem):
    module = load_recipe(RECIPES[1])
    outputs = airway_fixture()
    expected = {"metadataColumns": ["id", "dex", "celltype", "geo_id"], "geneCount": 1}
    module.validate_tables(outputs, expected)
    if problem == "pair":
        outputs["metadata"] = outputs["metadata"].replace(b"treated", b"control", 1)
    elif problem == "column":
        outputs["counts"] = outputs["counts"].replace(b"S0,S1", b"S1,S0")
    else:
        replacements = {"negative": b"-1.0", "fractional": b"0.5", "nan": b"nan"}
        outputs["counts"] = outputs["counts"].replace(b"1.0", replacements[problem], 1)
    with pytest.raises(ValueError):
        module.validate_tables(outputs, expected)
