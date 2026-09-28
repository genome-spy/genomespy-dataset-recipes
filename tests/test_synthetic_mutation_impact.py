"""Check the synthetic fixture's independent scientific contract."""

import json

import pytest
from test_python_migration_recipes import load_recipe


@pytest.mark.parametrize("problem", [None, "position", "base", "score", "length"])
def test_synthetic_reference_checks_positions_bases_and_periodic_scores(problem):
    recipe = load_recipe("synthetic-mutation-impact")
    params = {
        "assembly": "synthetic-v1",
        "chrom": "chrSynthetic",
        "start": 100,
        "length": 5,
        "valueOffset": 5,
        "valueStep": 3,
        "valueModulus": 11,
        "valueDivisor": 20,
    }
    data = {
        "assembly": "synthetic-v1",
        "chrom": "chrSynthetic",
        "rows": [
            {"position": 100 + i, "base": "A", "value": score}
            for i, score in enumerate([0.25, 0.4, 0.55, 0.7, 0.3])
        ],
    }
    if problem == "position":
        data["rows"][1]["position"] = 100
    elif problem == "base":
        data["rows"][0]["base"] = "AC"
    elif problem == "score":
        data["rows"][4]["value"] = 0.85
    elif problem == "length":
        data["rows"].pop()
    raw = json.dumps(data).encode()
    if problem is None:
        recipe.validate_reference(raw, params)
    else:
        with pytest.raises(ValueError):
            recipe.validate_reference(raw, params)
