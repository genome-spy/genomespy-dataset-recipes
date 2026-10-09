"""Guard PBMC alignment and aggregation without loading scientific dependencies."""

import copy
import hashlib

import pytest
from test_python_migration_recipes import load_recipe


def small_bundle():
    return {
        "cells": [
            {"cell": "a", "cell_order": 0, "cell_type": "T", "n_counts": 10},
            {"cell": "b", "cell_order": 1, "cell_type": "T", "n_counts": 20},
            {"cell": "c", "cell_order": 2, "cell_type": "B", "n_counts": 30},
        ],
        "expression": [[1.0], [3.0], [6.0]],
        "umap_expression": [[2.0], [4.0], [8.0]],
        "markers": [{"gene": "GENE1"}],
        "umap_genes": ["GENE2"],
        "umap": [[-1.0, 0.0], [1.0, 2.0], [3.0, -2.0]],
        "umap_domains": {"x": [-2.0, 4.0], "y": [-3.0, 3.0]},
        "groups": [
            {"cell_type": "T", "start": 0, "end": 2, "count": 2},
            {"cell_type": "B", "start": 2, "end": 3, "count": 1},
        ],
        "means": [
            {"cell_type": "T", "gene": "GENE1", "mean_expression": 2.0},
            {"cell_type": "B", "gene": "GENE1", "mean_expression": 6.0},
        ],
        "n_counts_limit": 30,
    }


@pytest.mark.parametrize(
    "problem",
    [
        None,
        "mean",
        "label",
        "umap",
        "duplicate",
        "partition",
        "negative",
        "missing_mean",
    ],
)
def test_pbmc_validates_cell_alignment_and_group_summaries(problem):
    recipe = load_recipe("scanpy-pbmc3k-marker-expression")
    data = copy.deepcopy(small_bundle())
    if problem == "mean":
        data["means"][0]["mean_expression"] = 3.0
    elif problem == "label":
        data["cells"][1]["cell_type"] = "B"
    elif problem == "umap":
        data["umap"].pop()
    elif problem == "duplicate":
        data["cells"][1]["cell"] = "a"
    elif problem == "partition":
        data["groups"][1]["start"] = 1
    elif problem == "negative":
        data["umap_expression"][0][0] = -1.0
    elif problem == "missing_mean":
        data["means"].pop()
    if problem is None:
        recipe.validate_bundle(data)
    else:
        with pytest.raises(ValueError):
            recipe.validate_bundle(data)


def test_pbmc_rejects_changed_producer_before_execution(tmp_path, monkeypatch):
    recipe = load_recipe("scanpy-pbmc3k-marker-expression")
    monkeypatch.setattr(recipe, "ROOT", tmp_path)
    cache = tmp_path / "download"
    cache.mkdir()
    (cache / "producer.py").write_bytes(b"changed!")

    def no_network(*args, **kwargs):
        pytest.fail("Corrupt pinned producer must not be replaced")

    monkeypatch.setattr(recipe, "urlopen", no_network)
    with pytest.raises(ValueError, match="SHA-256"):
        recipe.acquire(
            {
                "filename": "producer.py",
                "fileSizeBytes": 8,
                "sha256": hashlib.sha256(b"original").hexdigest(),
            }
        )
