import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from tools import publish_dataset as publish


def make_artifact(tmp_path: Path) -> publish.Artifact:
    path = tmp_path / "result.tsv"
    path.write_text("value\n1\n", encoding="utf-8")
    return publish.Artifact(
        relative_path="output/result.tsv",
        local_path=path,
        key="datasets/example/v1/result.tsv",
        public_url="https://data.genomespy.app/datasets/example/v1/result.tsv",
        file_size_bytes=path.stat().st_size,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        content_type="text/tab-separated-values; charset=utf-8",
    )


def test_parser_requires_explicit_recipe_for_write_actions(tmp_path: Path) -> None:
    config = tmp_path / "missing.toml"
    with pytest.raises(SystemExit):
        publish.parse_args(
            ["publish", "--bucket", "example-bucket", "--config", str(config)]
        )
    args = publish.parse_args(
        [
            "publish",
            "example-recipe",
            "--bucket",
            "example-bucket",
            "--config",
            str(config),
        ]
    )
    assert args.recipes == ["example-recipe"]


def test_status_can_scan_without_explicit_recipes(tmp_path: Path) -> None:
    args = publish.parse_args(
        [
            "status",
            "--bucket",
            "example-bucket",
            "--config",
            str(tmp_path / "missing.toml"),
        ]
    )
    assert args.recipes == []


def test_local_config_supplies_named_targets_and_cli_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AWS_PROFILE", "stale-profile")
    monkeypatch.setenv("AWS_REGION", "ap-southeast-1")
    monkeypatch.setenv("GENOMESPY_DATA_BUCKET", "stale-bucket")
    config = tmp_path / "publish.toml"
    config.write_text(
        """
default_target = "test"

[targets.test]
bucket = "test-bucket"
profile = "publisher"
region = "us-east-1"
expected_bucket_owner = "123456789012"
skip_public_verification = true

[targets.production]
bucket = "production-bucket"
region = "eu-north-1"
""".strip(),
        encoding="utf-8",
    )

    default_args = publish.parse_args(["status", "--config", str(config)])
    production_args = publish.parse_args(
        ["status", "--config", str(config), "--target", "production"]
    )
    override_args = publish.parse_args(
        [
            "status",
            "--config",
            str(config),
            "--bucket",
            "one-off-bucket",
            "--region",
            "ca-central-1",
            "--no-skip-public-verification",
        ]
    )

    assert default_args.target == "test"
    assert default_args.bucket == "test-bucket"
    assert default_args.profile == "publisher"
    assert default_args.region == "us-east-1"
    assert default_args.expected_bucket_owner == "123456789012"
    assert default_args.skip_public_verification
    assert production_args.bucket == "production-bucket"
    assert production_args.region == "eu-north-1"
    assert not production_args.skip_public_verification
    assert override_args.bucket == "one-off-bucket"
    assert override_args.region == "ca-central-1"
    assert not override_args.skip_public_verification


def test_local_config_rejects_unknown_keys(tmp_path: Path) -> None:
    config = tmp_path / "publish.toml"
    config.write_text(
        '[targets.test]\nbucket = "test-bucket"\nbukcet = "typo"\n',
        encoding="utf-8",
    )

    with pytest.raises(publish.PublicationError, match="unknown key"):
        publish.load_config(config)


def test_load_release_uses_only_manifest_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recipes_dir = tmp_path / "recipes"
    recipe = recipes_dir / "example-recipe"
    output = recipe / "output"
    output.mkdir(parents=True)
    accepted = output / "accepted.tsv"
    accepted.write_text("x\n1\n", encoding="utf-8")
    (output / "local-diagnostic.tsv").write_text("ignore me\n", encoding="utf-8")
    sha256 = hashlib.sha256(accepted.read_bytes()).hexdigest()
    provenance = {
        "schemaVersion": 2,
        "recipeId": "example-recipe",
        "releaseId": "v1",
        "sources": [{}],
        "outputs": {"accepted": {"path": "output/accepted.tsv"}},
        "distribution": {
            "baseUrl": "https://data.genomespy.app/datasets/example-recipe/v1/",
            "artifacts": {
                "output/accepted.tsv": {
                    "fileSizeBytes": accepted.stat().st_size,
                    "sha256": sha256,
                }
            },
        },
    }
    (recipe / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")
    (recipe / "RIGHTS.md").write_text(
        "## Decision\n\nEligible for GenomeSpy-managed hosting.\n",
        encoding="utf-8",
    )
    (recipe / "README.md").write_text("# Example\n", encoding="utf-8")
    monkeypatch.setattr(publish, "RECIPES_DIR", recipes_dir)
    monkeypatch.setattr(publish, "require_committed_recipe", lambda _: "a" * 40)

    release = publish.load_release("example-recipe")

    assert [artifact.relative_path for artifact in release.artifacts] == [
        "output/accepted.tsv"
    ]


def test_load_release_rejects_changed_local_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recipes_dir = tmp_path / "recipes"
    recipe = recipes_dir / "example-recipe"
    output = recipe / "output"
    output.mkdir(parents=True)
    accepted = output / "accepted.tsv"
    accepted.write_text("changed\n", encoding="utf-8")
    provenance = {
        "schemaVersion": 2,
        "recipeId": "example-recipe",
        "releaseId": "v1",
        "sources": [{}],
        "outputs": {"accepted": {"path": "output/accepted.tsv"}},
        "distribution": {
            "baseUrl": "https://data.genomespy.app/datasets/example-recipe/v1/",
            "artifacts": {
                "output/accepted.tsv": {
                    "fileSizeBytes": accepted.stat().st_size,
                    "sha256": "0" * 64,
                }
            },
        },
    }
    (recipe / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")
    (recipe / "RIGHTS.md").write_text(
        "## Decision\n\nEligible for GenomeSpy-managed hosting.\n", encoding="utf-8"
    )
    (recipe / "README.md").write_text("# Example\n", encoding="utf-8")
    monkeypatch.setattr(publish, "RECIPES_DIR", recipes_dir)

    with pytest.raises(publish.PublicationError, match="SHA-256 changed"):
        publish.load_release("example-recipe")


def test_status_load_does_not_require_local_artifacts_or_a_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recipes_dir = tmp_path / "recipes"
    recipe = recipes_dir / "example-recipe"
    recipe.mkdir(parents=True)
    provenance = {
        "schemaVersion": 2,
        "recipeId": "example-recipe",
        "releaseId": "v1",
        "distribution": {
            "baseUrl": "https://data.genomespy.app/datasets/example-recipe/v1/",
            "artifacts": {
                "output/absent.tsv": {
                    "fileSizeBytes": 12,
                    "sha256": "a" * 64,
                }
            },
        },
    }
    (recipe / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")
    (recipe / "RIGHTS.md").write_text(
        "## Decision\n\nEligible for GenomeSpy-managed hosting.\n", encoding="utf-8"
    )
    monkeypatch.setattr(publish, "RECIPES_DIR", recipes_dir)

    release = publish.load_release(
        "example-recipe", validate_local=False, require_commit=False
    )

    assert release.git_commit == ""
    assert release.artifacts[0].local_path == recipe / "output/absent.tsv"

    provenance["distribution"]["artifacts"]["output/absent.tsv"][  # type: ignore[index]
        "fileSizeBytes"
    ] = True
    (recipe / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")
    with pytest.raises(publish.PublicationError, match="invalid size"):
        publish.load_release(
            "example-recipe", validate_local=False, require_commit=False
        )


def test_discovery_only_includes_hosted_artifact_inventories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recipes_dir = tmp_path / "recipes"
    for recipe_id, provenance in {
        "eligible": {
            "schemaVersion": 2,
            "distribution": {
                "baseUrl": "https://data.genomespy.app/datasets/eligible/v1/",
                "artifacts": {"output/data.tsv": {}},
            },
        },
        "local-only": {"schemaVersion": 2, "distribution": None},
        "legacy": {"schemaVersion": 1},
    }.items():
        recipe = recipes_dir / recipe_id
        recipe.mkdir(parents=True)
        (recipe / "provenance.json").write_text(
            json.dumps(provenance), encoding="utf-8"
        )
    monkeypatch.setattr(publish, "RECIPES_DIR", recipes_dir)

    assert publish.discover_publishable_recipes() == ["eligible"]


def test_status_reports_missing_and_wrong_sized_artifacts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    first = make_artifact(tmp_path)
    second = publish.Artifact(
        relative_path="output/other.tsv",
        local_path=tmp_path / "other.tsv",
        key="datasets/example/v1/other.tsv",
        public_url="https://data.genomespy.app/datasets/example/v1/other.tsv",
        file_size_bytes=20,
        sha256="b" * 64,
        content_type="text/tab-separated-values; charset=utf-8",
    )
    release = publish.Release(
        recipe_id="example",
        release_id="v1",
        recipe_dir=tmp_path,
        base_url="https://data.genomespy.app/datasets/example/v1/",
        git_commit="",
        artifacts=(first, second),
    )
    aws = publish.AwsCli(None, None, None)
    aws.json = lambda *args: {  # type: ignore[method-assign]
        "Contents": [{"Key": first.key, "Size": first.file_size_bytes + 1}]
    }

    complete = publish.print_release_status(release, aws, "example-bucket")

    output = capsys.readouterr().out
    assert not complete
    assert "0/2 artifacts match S3, 1 missing, 1 size conflicts" in output
    assert "missing: output/other.tsv" in output
    assert "size conflict: output/result.tsv" in output
    assert "s3://example-bucket/datasets/example/v1/other.tsv" in output


def test_list_release_objects_paginates() -> None:
    aws = publish.AwsCli(None, "eu-north-1", "123456789012")
    calls: list[tuple[str, ...]] = []

    def fake_json(*arguments: str) -> dict[str, object]:
        calls.append(arguments)
        if "--continuation-token" not in arguments:
            return {
                "Contents": [{"Key": "datasets/example/v1/a.tsv", "Size": 1}],
                "IsTruncated": True,
                "NextContinuationToken": "next-page",
            }
        return {
            "Contents": [{"Key": "datasets/example/v1/b.tsv", "Size": 2}],
            "IsTruncated": False,
        }

    aws.json = fake_json  # type: ignore[method-assign]

    objects = publish.list_release_objects(
        aws, "example-bucket", "datasets/example/v1/"
    )

    assert objects == {
        "datasets/example/v1/a.tsv": 1,
        "datasets/example/v1/b.tsv": 2,
    }
    assert calls[1][-2:] == ("--continuation-token", "next-page")


def test_remote_comparison_requires_identity_and_headers(tmp_path: Path) -> None:
    artifact = make_artifact(tmp_path)
    matching = {
        "ContentLength": artifact.file_size_bytes,
        "ContentType": artifact.content_type,
        "CacheControl": publish.CACHE_CONTROL,
        "Metadata": {"sha256": artifact.sha256},
    }
    assert publish.compare_remote(None, artifact).status == "missing"
    assert publish.compare_remote(matching, artifact).status == "matching"
    matching["Metadata"] = {"sha256": "0" * 64}
    assert publish.compare_remote(matching, artifact).status == "conflict"


def test_put_object_is_conditional_and_checksummed(tmp_path: Path) -> None:
    artifact = make_artifact(tmp_path)
    release = publish.Release(
        recipe_id="example",
        release_id="v1",
        recipe_dir=tmp_path,
        base_url="https://data.genomespy.app/datasets/example/v1/",
        git_commit="a" * 40,
        artifacts=(artifact,),
    )
    aws = publish.AwsCli("publisher", "eu-north-1", "123456789012")

    command = publish.put_object_arguments(aws, "example-bucket", release, artifact)

    assert command[command.index("--if-none-match") + 1] == "*"
    assert "--checksum-sha256" in command
    assert command[command.index("--expected-bucket-owner") + 1] == "123456789012"
    assert command[command.index("--profile") + 1] == "publisher"
    assert command[command.index("--region") + 1] == "eu-north-1"


def test_rights_decision_must_be_exactly_positive() -> None:
    assert publish.hosting_is_eligible(
        "# Rights\n\n## Decision\n\n"
        "Eligible for GenomeSpy-managed hosting under the conditions above.\n"
    )
    assert not publish.hosting_is_eligible(
        "## Decision\n\nNot eligible for GenomeSpy-managed hosting.\n"
    )
    assert not publish.hosting_is_eligible("Eligible for GenomeSpy-managed hosting.\n")


def test_external_artifact_source_requires_an_allowed_root(tmp_path: Path) -> None:
    recipe = tmp_path / "recipes/example"
    output = recipe / "output"
    source_root = tmp_path / "source"
    output.mkdir(parents=True)
    source_root.mkdir()
    source = source_root / "result.tsv"
    source.write_text("x\n", encoding="utf-8")
    link = output / "result.tsv"
    link.symlink_to(source)

    with pytest.raises(publish.PublicationError, match="--allow-source-root"):
        publish.validate_artifact_source(link, recipe, ())

    assert publish.validate_artifact_source(link, recipe, (source_root,)) == source


def test_missing_command_is_reported_cleanly(tmp_path: Path) -> None:
    with pytest.raises(publish.PublicationError, match="Could not run"):
        publish.run(["command-that-does-not-exist-12345"], cwd=tmp_path)


def test_recipe_source_commit_is_stable_for_unrelated_commits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(
        command: list[str],
        *,
        check: bool = True,
        cwd: Path = publish.ROOT,
    ) -> subprocess.CompletedProcess[str]:
        del check, cwd
        calls.append(command)
        stdout = "b" * 40 + "\n" if command[1:4] == ["log", "-1", "--format=%H"] else ""
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr(publish, "run", fake_run)

    commit = publish.require_committed_recipe(publish.ROOT / "recipes/example-recipe")

    assert commit == "b" * 40
    assert [
        "git",
        "diff",
        "--quiet",
        "HEAD",
        "--",
        "recipes/example-recipe",
    ] in calls
    assert [
        "git",
        "log",
        "-1",
        "--format=%H",
        "--",
        "recipes/example-recipe",
    ] in calls


def test_rejects_unsafe_artifact_paths() -> None:
    for value in (
        "../secret",
        "/output/file",
        "output/../secret",
        "output/./secret",
        "output//secret",
        "output",
    ):
        with pytest.raises(publish.PublicationError):
            publish.validate_artifact_path(value)


def test_rejects_unsafe_recipe_and_release_ids() -> None:
    with pytest.raises(publish.PublicationError, match="invalid recipe ID"):
        publish.release_prefix(
            "https://data.genomespy.app/datasets/../outside/v1/", "../outside", "v1"
        )
    with pytest.raises(publish.PublicationError, match="invalid release ID"):
        publish.release_prefix(
            "https://data.genomespy.app/datasets/example/../",
            "example",
            "../",
        )
