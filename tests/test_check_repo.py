import json
from pathlib import Path

import pytest

from tools.check_repo import check_file, check_recipe, check_spec_values, is_cc0_covered


def test_cc0_scope_covers_repository_authored_material() -> None:
    for path in (
        Path("tools/publish_dataset.py"),
        Path("tests/test_publish_dataset.py"),
        Path("docs/publishing.md"),
        Path("recipes/example/provenance.json"),
    ):
        assert is_cc0_covered(path)

    for path in (
        Path("LICENSES/CC0-1.0.txt"),
        Path("uv.lock"),
        Path("recipes/example/scripts/prepare.py.lock"),
    ):
        assert not is_cc0_covered(path)


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


def test_import_urls_are_distinct_from_data_urls() -> None:
    errors = check_spec_values(
        "example",
        "overview.json",
        {
            "vconcat": [
                {"import": {"url": "track.json"}},
                {"data": {"url": "track.json"}},
            ]
        },
    )

    assert errors == ["example: non-output data URL in overview.json: track.json"]


@pytest.mark.parametrize(
    "url", ["https://example.org/track.json", "/track.json", "../output/data.json"]
)
def test_imports_must_reference_local_specs(url: str) -> None:
    errors = check_spec_values("example", "overview.json", {"import": {"url": url}})

    assert errors == [
        f"example: authored JSON reference must be local in overview.json: {url}"
    ]


def test_accepts_local_remote_bookmark_file() -> None:
    errors = check_spec_values(
        "example",
        "overview.json",
        {"bookmarks": {"remote": {"url": "bookmarks.json"}}},
    )

    assert errors == []


@pytest.mark.parametrize(
    "url", ["https://example.org/bookmarks.json", "../bookmarks.json"]
)
def test_remote_bookmarks_must_reference_local_authored_json(url: str) -> None:
    errors = check_spec_values(
        "example",
        "overview.json",
        {"bookmarks": {"remote": {"url": url}}},
    )

    assert errors == [
        f"example: authored JSON reference must be local in overview.json: {url}"
    ]


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
        '{"schemaVersion": 1, "releaseId": "v1", "recipeId": "wrong", '
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
        '{"schemaVersion": 2, "releaseId": "v1", '
        '"recipeId": "example-recipe", '
        '"sources": [{}], "outputs": {"x": {}}, '
        '"distribution": {"baseUrl": '
        '"https://data.genomespy.app/datasets/another-recipe/v1/"}}\n',
        encoding="utf-8",
    )

    errors = check_recipe(recipe)

    assert errors == ["example-recipe: invalid distribution baseUrl"]


def test_recipe_requires_release_id(tmp_path: Path) -> None:
    recipe = tmp_path / "example-recipe"
    recipe.mkdir()
    (recipe / "README.md").write_text("# Example\n", encoding="utf-8")
    (recipe / "RIGHTS.md").write_text("# Rights\n", encoding="utf-8")
    (recipe / "provenance.json").write_text(
        '{"schemaVersion": 1, "recipeId": "example-recipe", '
        '"sources": [{}], "outputs": {"x": {}}}\n',
        encoding="utf-8",
    )

    errors = check_recipe(recipe)

    assert errors == [
        "example-recipe: missing provenance key releaseId",
        "example-recipe: releaseId must match v1, v2, and so on",
    ]


def test_release_id_must_be_version_label(tmp_path: Path) -> None:
    recipe = tmp_path / "example-recipe"
    recipe.mkdir()
    (recipe / "README.md").write_text("# Example\n", encoding="utf-8")
    (recipe / "RIGHTS.md").write_text("# Rights\n", encoding="utf-8")
    (recipe / "provenance.json").write_text(
        '{"schemaVersion": 1, "releaseId": "1", '
        '"recipeId": "example-recipe", '
        '"sources": [{}], "outputs": {"x": {}}}\n',
        encoding="utf-8",
    )

    errors = check_recipe(recipe)

    assert errors == ["example-recipe: releaseId must match v1, v2, and so on"]


def test_distribution_url_must_match_release_id(tmp_path: Path) -> None:
    recipe = tmp_path / "example-recipe"
    recipe.mkdir()
    (recipe / "README.md").write_text("# Example\n", encoding="utf-8")
    (recipe / "RIGHTS.md").write_text("# Rights\n", encoding="utf-8")
    (recipe / "provenance.json").write_text(
        '{"schemaVersion": 1, "releaseId": "v2", '
        '"recipeId": "example-recipe", '
        '"sources": [{}], "outputs": {"x": {}}, '
        '"distribution": {"baseUrl": '
        '"https://data.genomespy.app/datasets/example-recipe/v1/"}}\n',
        encoding="utf-8",
    )

    errors = check_recipe(recipe)

    assert errors == ["example-recipe: invalid distribution baseUrl"]


def test_valid_distribution_requires_artifact_manifest(tmp_path: Path) -> None:
    recipe = tmp_path / "example-recipe"
    recipe.mkdir()
    (recipe / "README.md").write_text("# Example\n", encoding="utf-8")
    (recipe / "RIGHTS.md").write_text("# Rights\n", encoding="utf-8")
    (recipe / "provenance.json").write_text(
        '{"schemaVersion": 2, "releaseId": "v1", '
        '"recipeId": "example-recipe", '
        '"sources": [{}], "outputs": {"x": {}}, '
        '"distribution": {"baseUrl": '
        '"https://data.genomespy.app/datasets/example-recipe/v1/"}}\n',
        encoding="utf-8",
    )

    errors = check_recipe(recipe)

    assert errors == [
        "example-recipe: distribution artifacts must be a non-empty object"
    ]


def test_artifact_manifest_rejects_boolean_size_and_noncanonical_path(
    tmp_path: Path,
) -> None:
    recipe = tmp_path / "example-recipe"
    recipe.mkdir()
    (recipe / "README.md").write_text("# Example\n", encoding="utf-8")
    (recipe / "RIGHTS.md").write_text("# Rights\n", encoding="utf-8")
    provenance = {
        "schemaVersion": 2,
        "releaseId": "v1",
        "recipeId": "example-recipe",
        "sources": [{}],
        "outputs": {"x": {}},
        "distribution": {
            "baseUrl": "https://data.genomespy.app/datasets/example-recipe/v1/",
            "artifacts": {
                "output/./data.tsv": {
                    "fileSizeBytes": True,
                    "sha256": "a" * 64,
                }
            },
        },
    }
    (recipe / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")

    errors = check_recipe(recipe)

    assert "example-recipe: invalid artifact path output/./data.tsv" in errors
    assert "example-recipe: invalid artifact size for output/./data.tsv" in errors
