"""Check historical LUAD export identity without network access."""

import pytest
from test_python_migration_recipes import load_recipe


@pytest.mark.parametrize(
    "problem", [None, "sample", "width", "type", "historical", "duplicate"]
)
def test_luad_export_contract(problem):
    recipe = load_recipe("cbioportal-tcga-luad-alterations")
    rows = [
        ["track_name", "track_type", "TCGA-A", "TCGA-B"],
        ["Dicipivirus", "HEATMAP", "", "0.4"],
        ["GENE", "MUTATIONS", "MISSENSE", ""],
    ]
    expected = {
        "sampleCount": 2,
        "trackCount": 2,
        "trackTypes": {"HEATMAP": 1, "MUTATIONS": 1},
        "historicalMicrobiomeTrack": ["Dicipivirus", "HEATMAP"],
    }
    if problem == "sample":
        rows[0][3] = "TCGA-A"
    elif problem == "width":
        rows[1].pop()
    elif problem == "type":
        rows[2][1] = "CNA"
    elif problem == "historical":
        rows[1][0] = "Replacement"
    elif problem == "duplicate":
        rows.append(rows[2].copy())
        expected["trackCount"] = 3
        expected["trackTypes"]["MUTATIONS"] = 2
    outputs = {"alterations": ("\n".join("\t".join(r) for r in rows) + "\n").encode()}
    if problem is None:
        recipe.validate_tables(outputs, expected)
    else:
        with pytest.raises(ValueError):
            recipe.validate_tables(outputs, expected)
