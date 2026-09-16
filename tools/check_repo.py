#!/usr/bin/env python3
"""Check the repository contract without reading ignored dataset artifacts."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ROOT_FILES = {
    ".gitignore",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "LICENSE-SCOPE.md",
    "README.md",
    "pyproject.toml",
    "uv.lock",
}
WORKING_DIRECTORY_NAMES = {"download", "work", "output"}
DATA_SUFFIXES = {
    ".bai",
    ".bam",
    ".bcf",
    ".bed",
    ".bigwig",
    ".bw",
    ".csv",
    ".fa",
    ".fai",
    ".fasta",
    ".gff",
    ".gff3",
    ".gz",
    ".parquet",
    ".rdata",
    ".rds",
    ".sam",
    ".tar",
    ".tbi",
    ".tsv",
    ".vcf",
    ".zip",
}
MAX_TRACKED_FILE_BYTES = 1_000_000
SECRET_PATTERNS = {
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private key": re.compile(r"BEGIN (?:EC |OPENSSH |RSA )?PRIVATE KEY"),
    "assigned secret": re.compile(
        r"(?i)(?:api[_-]?key|secret|token)\s*[:=]\s*['\"][^'\"]{8,}"
    ),
}
ABSOLUTE_LOCAL_PATH = re.compile(r"(?:/" + r"Users/|/" + r"home/|[A-Za-z]:\\Users\\)")
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
SPDX_IDENTIFIER = re.compile(r"SPDX-License-" r"Identifier:\s*([^\s]+)")
RECIPE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RELEASE_ID = re.compile(r"^v[1-9][0-9]*$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
RELEASE_URL = re.compile(
    r"^https://data[.]genomespy[.]app/datasets/"
    r"(?P<recipe>[a-z0-9]+(?:-[a-z0-9]+)*)/"
    r"(?P<release>v[1-9][0-9]*)/$"
)


def repository_files(root: Path = ROOT) -> list[Path]:
    """Return tracked and unignored untracked repository files."""

    result = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    files = [root / item for item in result.stdout.decode().split("\0") if item]
    return [file for file in files if file.is_file()]


def is_cc0_covered(relative: Path) -> bool:
    """Return whether the path is within the repository's CC0 scope."""

    if relative.parts and relative.parts[0] == "LICENSES":
        return False
    return relative.name != "uv.lock" and relative.suffix != ".lock"


def check_file(root: Path, file: Path) -> list[str]:
    """Return contract errors for one repository file."""

    errors: list[str] = []
    relative = file.relative_to(root)
    if WORKING_DIRECTORY_NAMES.intersection(relative.parts):
        errors.append(f"tracked working artifact: {relative}")
    if file.suffix.lower() in DATA_SUFFIXES:
        errors.append(f"tracked data-like file: {relative}")
    if file.stat().st_size > MAX_TRACKED_FILE_BYTES:
        errors.append(
            f"tracked file exceeds {MAX_TRACKED_FILE_BYTES} bytes: {relative}"
        )

    try:
        text = file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        errors.append(f"tracked binary file: {relative}")
        return errors

    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            errors.append(f"possible {label} in {relative}")
    if ABSOLUTE_LOCAL_PATH.search(text):
        errors.append(f"absolute local path in {relative}")

    if is_cc0_covered(relative):
        identifiers = SPDX_IDENTIFIER.findall(text)
        if any(identifier != "CC0-1.0" for identifier in identifiers):
            errors.append(f"non-CC0 SPDX marker in CC0-covered file: {relative}")

    if file.suffix.lower() == ".md":
        errors.extend(check_markdown_links(root, file, text))
    return errors


def check_markdown_links(root: Path, file: Path, text: str) -> list[str]:
    """Return errors for broken relative Markdown links."""

    errors: list[str] = []
    for raw_target in MARKDOWN_LINK.findall(text):
        target = raw_target.strip().strip("<>").split(maxsplit=1)[0]
        if target.startswith(("#", "http://", "https://", "mailto:")):
            continue
        path_text = unquote(target.split("#", 1)[0])
        if not path_text:
            continue
        resolved = (file.parent / path_text).resolve()
        if not resolved.is_relative_to(root.resolve()) or not resolved.exists():
            relative = file.relative_to(root)
            errors.append(f"broken relative link in {relative}: {target}")
    return errors


def check_recipe(recipe_dir: Path) -> list[str]:
    """Return errors for one concrete recipe directory."""

    errors: list[str] = []
    required = {"README.md", "RIGHTS.md", "provenance.json"}
    missing = sorted(name for name in required if not (recipe_dir / name).is_file())
    errors.extend(f"{recipe_dir.name}: missing {name}" for name in missing)
    if missing:
        return errors

    try:
        provenance: Any = json.loads(
            (recipe_dir / "provenance.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as error:
        return [f"{recipe_dir.name}: invalid provenance.json: {error}"]
    if not isinstance(provenance, dict):
        return [f"{recipe_dir.name}: provenance root must be an object"]

    required_keys = {
        "schemaVersion",
        "releaseId",
        "recipeId",
        "sources",
        "outputs",
    }
    absent_keys = sorted(required_keys.difference(provenance))
    errors.extend(
        f"{recipe_dir.name}: missing provenance key {key}" for key in absent_keys
    )

    recipe_id = provenance.get("recipeId")
    schema_version = provenance.get("schemaVersion")
    if schema_version not in {1, 2}:
        errors.append(f"{recipe_dir.name}: unsupported provenance schemaVersion")
    if recipe_id != recipe_dir.name or not isinstance(recipe_id, str):
        errors.append(f"{recipe_dir.name}: recipeId must match the directory name")
    elif not RECIPE_ID.fullmatch(recipe_id):
        errors.append(f"{recipe_dir.name}: recipeId is not lowercase kebab-case")

    release_id = provenance.get("releaseId")
    if not isinstance(release_id, str) or not RELEASE_ID.fullmatch(release_id):
        errors.append(f"{recipe_dir.name}: releaseId must match v1, v2, and so on")

    sources = provenance.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append(f"{recipe_dir.name}: sources must be a non-empty list")
    elif not all(isinstance(source, dict) for source in sources):
        errors.append(f"{recipe_dir.name}: source entries must be objects")

    distribution = provenance.get("distribution")
    if distribution is not None:
        if not isinstance(distribution, dict):
            errors.append(f"{recipe_dir.name}: distribution must be an object")
        else:
            base_url = distribution.get("baseUrl")
            match = (
                RELEASE_URL.fullmatch(base_url) if isinstance(base_url, str) else None
            )
            if (
                match is None
                or match.group("recipe") != recipe_dir.name
                or match.group("release") != release_id
            ):
                errors.append(f"{recipe_dir.name}: invalid distribution baseUrl")
            elif schema_version == 2:
                artifacts = distribution.get("artifacts")
                if not isinstance(artifacts, dict) or not artifacts:
                    errors.append(
                        f"{recipe_dir.name}: distribution artifacts must be "
                        "a non-empty object"
                    )
                else:
                    for artifact_path, identity in artifacts.items():
                        if not isinstance(artifact_path, str):
                            errors.append(
                                f"{recipe_dir.name}: artifact paths must be strings"
                            )
                            continue
                        manifest_path = PurePosixPath(artifact_path)
                        if (
                            manifest_path.as_posix() != artifact_path
                            or manifest_path.is_absolute()
                            or len(manifest_path.parts) < 2
                            or manifest_path.parts[0] != "output"
                            or any(
                                part in {"", ".", ".."} for part in manifest_path.parts
                            )
                        ):
                            errors.append(
                                f"{recipe_dir.name}: invalid artifact path "
                                f"{artifact_path}"
                            )
                        if not isinstance(identity, dict):
                            errors.append(
                                f"{recipe_dir.name}: artifact identities must be "
                                "objects"
                            )
                            continue
                        size = identity.get("fileSizeBytes")
                        sha256 = identity.get("sha256")
                        if type(size) is not int or size < 0:
                            errors.append(
                                f"{recipe_dir.name}: invalid artifact size for "
                                f"{artifact_path}"
                            )
                        if not isinstance(sha256, str) or not SHA256.fullmatch(sha256):
                            errors.append(
                                f"{recipe_dir.name}: invalid artifact SHA-256 for "
                                f"{artifact_path}"
                            )

    outputs = provenance.get("outputs")
    if not isinstance(outputs, dict) or not outputs:
        errors.append(f"{recipe_dir.name}: outputs must be a non-empty object")
    else:
        for output in outputs.values():
            if not isinstance(output, dict):
                errors.append(f"{recipe_dir.name}: output entries must be objects")
                continue
            path = output.get("path")
            if path is not None and (
                not isinstance(path, str) or not path.startswith("output/")
            ):
                errors.append(f"{recipe_dir.name}: output path must start with output/")

    for script in sorted((recipe_dir / "scripts").glob("*.py")):
        script_text = script.read_text(encoding="utf-8")
        if "# /// script" not in script_text:
            errors.append(
                f"{recipe_dir.name}: missing PEP 723 metadata in {script.name}"
            )

    for spec in sorted((recipe_dir / "specs").rglob("*.json")):
        try:
            value = json.loads(spec.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            errors.append(f"{recipe_dir.name}: invalid spec {spec.name}: {error}")
            continue
        errors.extend(check_spec_values(recipe_dir.name, spec.name, value))
    return errors


def walk_json(
    value: Any, path: tuple[str, ...] = ()
) -> Iterable[tuple[tuple[str, ...], Any]]:
    """Yield every object key path and value recursively, ignoring array indexes."""

    if isinstance(value, dict):
        for key, child in value.items():
            child_path = (*path, key)
            yield child_path, child
            yield from walk_json(child, child_path)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child, path)


def check_spec_values(recipe_id: str, spec_name: str, value: Any) -> list[str]:
    """Check local spec imports, output data URLs, and embedded tables."""

    errors: list[str] = []
    for path, child in walk_json(value):
        key = path[-1]
        if key == "url" and isinstance(child, str):
            if path[-2:] == ("import", "url"):
                import_path = PurePosixPath(child)
                if (
                    import_path.is_absolute()
                    or ".." in import_path.parts
                    or ":" in child
                    or "\\" in child
                    or import_path.suffix != ".json"
                ):
                    errors.append(
                        f"{recipe_id}: import must reference a local spec "
                        f"in {spec_name}: {child}"
                    )
                continue
            is_remote = child.startswith(("http://", "https://"))
            if is_remote:
                errors.append(f"{recipe_id}: remote data URL in {spec_name}: {child}")
            elif not is_remote and not child.startswith("../output/"):
                errors.append(
                    f"{recipe_id}: non-output data URL in {spec_name}: {child}"
                )
        if (
            key == "values"
            and isinstance(child, list)
            and any(isinstance(item, dict) and item for item in child)
        ):
            errors.append(f"{recipe_id}: embedded values in {spec_name}")
    return errors


def check_repository(root: Path = ROOT) -> list[str]:
    """Return all repository contract errors."""

    errors: list[str] = []
    missing_root = sorted(
        name for name in REQUIRED_ROOT_FILES if not (root / name).is_file()
    )
    errors.extend(f"missing root file: {name}" for name in missing_root)
    for file in repository_files(root):
        errors.extend(check_file(root, file))

    recipes_dir = root / "recipes"
    for recipe_dir in sorted(recipes_dir.iterdir()):
        if recipe_dir.is_dir() and recipe_dir.name != "_template":
            errors.extend(check_recipe(recipe_dir))
    return errors


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    return parser.parse_args()


def main() -> None:
    """Print repository errors and fail when any are found."""

    args = parse_args()
    errors = check_repository(args.root.resolve())
    if errors:
        for error in errors:
            print("ERROR: " + error)
        raise SystemExit(1)
    print("Repository checks passed.")


if __name__ == "__main__":
    main()
