from pathlib import Path

from tools.check_repo import check_file, check_recipe, check_spec_values


def test_rejects_data_in_working_directory(tmp_path: Path) -> None:
    artifact = tmp_path / "recipes" / "example" / "output" / "result.tsv"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("x\n1\n", encoding="utf-8")

    errors = check_file(tmp_path, artifact)

    assert any("tracked working artifact" in error for error in errors)
    assert any("tracked data-like file" in error for error in errors)


def test_rejects_large_tracked_file(tmp_path: Path) -> None:
    artifact = tmp_path / "large.bin"
    artifact.write_bytes(b"x" * 1_000_001)

    errors = check_file(tmp_path, artifact)

    assert any("exceeds 1000000 bytes" in error for error in errors)


def test_rejects_remote_data_url() -> None:
    errors = check_spec_values(
        "example",
        "overview.json",
        {"data": {"url": "https://example.org/data.tsv"}},
    )

    assert errors == [
        "example: remote data URL in overview.json: https://example.org/data.tsv"
    ]


def test_accepts_relative_output_url() -> None:
    errors = check_spec_values(
        "example",
        "overview.json",
        {"data": {"url": "../output/example.tsv"}},
    )

    assert errors == []


def test_accepts_empty_signal_value() -> None:
    errors = check_spec_values(
        "example",
        "overview.json",
        {"data": {"values": [{}]}},
    )

    assert errors == []


def test_rejects_embedded_data_rows() -> None:
    errors = check_spec_values(
        "example",
        "overview.json",
        {"data": {"values": [{"chrom": "chr1", "pos": 1}]}},
    )

    assert errors == ["example: embedded values in overview.json"]


def test_recipe_requires_rights_record(tmp_path: Path) -> None:
    recipe = tmp_path / "example-recipe"
    recipe.mkdir()
    for name in ("README.md", "provenance.json"):
        (recipe / name).write_text("{}\n", encoding="utf-8")

    errors = check_recipe(recipe)

    assert errors == ["example-recipe: missing RIGHTS.md"]


def test_recipe_id_must_match_directory(tmp_path: Path) -> None:
    recipe = tmp_path / "example-recipe"
    recipe.mkdir()
    (recipe / "README.md").write_text("# Example\n", encoding="utf-8")
    (recipe / "RIGHTS.md").write_text("# Rights\n", encoding="utf-8")
    (recipe / "provenance.json").write_text(
        '{"schemaVersion": 1, "recipeId": "wrong", '
        '"sources": [{}], "outputs": {"x": {}}}\n',
        encoding="utf-8",
    )

    errors = check_recipe(recipe)

    assert errors == ["example-recipe: recipeId must match the directory name"]


def test_distribution_url_must_match_recipe(tmp_path: Path) -> None:
    recipe = tmp_path / "example-recipe"
    recipe.mkdir()
    (recipe / "README.md").write_text("# Example\n", encoding="utf-8")
    (recipe / "RIGHTS.md").write_text("# Rights\n", encoding="utf-8")
    (recipe / "provenance.json").write_text(
        '{"schemaVersion": 1, "recipeId": "example-recipe", '
        '"sources": [{}], "outputs": {"x": {}}, '
        '"distribution": {"baseUrl": '
        '"https://data.genomespy.app/datasets/another-recipe/v1/"}}\n',
        encoding="utf-8",
    )

    errors = check_recipe(recipe)

    assert errors == ["example-recipe: invalid distribution baseUrl"]
