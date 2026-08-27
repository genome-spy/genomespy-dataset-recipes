#!/usr/bin/env python3
"""Check the repository contract without reading ignored dataset artifacts."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import yaml

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
WORKING_DIRECTORY_NAMES = {"download", "work", "output", "publish"}
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
RECIPE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def repository_files(root: Path = ROOT) -> list[Path]:
    """Return tracked and unignored untracked repository files."""

    result = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return [root / item for item in result.stdout.decode().split("\0") if item]


def is_cc0_covered(relative: Path) -> bool:
    """Return whether the path is within the repository's CC0 scope."""

    if relative.name == "README.md":
        return True
    parts = relative.parts
    return (
        len(parts) >= 4 and parts[0] == "recipes" and parts[2] in {"scripts", "specs"}
    )


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
        identifiers = re.findall(r"SPDX-License-Identifier:\s*([^\s]+)", text)
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


def load_yaml_mapping(file: Path) -> Mapping[str, Any]:
    """Load a YAML file and require an object at its root."""

    value = yaml.safe_load(file.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("root must be a mapping")
    return value


def check_recipe(recipe_dir: Path) -> list[str]:
    """Return errors for one concrete recipe directory."""

    errors: list[str] = []
    required = {
        "README.md",
        "RIGHTS.md",
        "provenance.json",
        "recipe.yaml",
        "sources.lock.json",
    }
    missing = sorted(name for name in required if not (recipe_dir / name).is_file())
    errors.extend(f"{recipe_dir.name}: missing {name}" for name in missing)
    if missing:
        return errors

    try:
        recipe = load_yaml_mapping(recipe_dir / "recipe.yaml")
    except (OSError, ValueError, yaml.YAMLError) as error:
        return [f"{recipe_dir.name}: invalid recipe.yaml: {error}"]

    required_keys = {"id", "title", "status", "kind", "sources", "outputs"}
    absent_keys = sorted(required_keys.difference(recipe))
    errors.extend(f"{recipe_dir.name}: missing recipe key {key}" for key in absent_keys)

    recipe_id = recipe.get("id")
    if recipe_id != recipe_dir.name or not isinstance(recipe_id, str):
        errors.append(f"{recipe_dir.name}: id must match the directory name")
    elif not RECIPE_ID.fullmatch(recipe_id):
        errors.append(f"{recipe_dir.name}: id is not lowercase kebab-case")
    if recipe.get("status") not in {"draft", "ready"}:
        errors.append(f"{recipe_dir.name}: status must be draft or ready")
    if recipe.get("kind") not in {"direct", "mirror", "transform"}:
        errors.append(f"{recipe_dir.name}: unknown recipe kind")

    sources = recipe.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append(f"{recipe_dir.name}: sources must be a non-empty list")
    else:
        for source in sources:
            if not isinstance(source, dict):
                errors.append(f"{recipe_dir.name}: source entries must be mappings")
                continue
            if source.get("redistribution") not in {
                "allowed",
                "prohibited",
                "unresolved",
            }:
                errors.append(f"{recipe_dir.name}: invalid redistribution value")
            evidence = source.get("rightsEvidence")
            if source.get("redistribution") == "allowed" and not isinstance(
                evidence, str
            ):
                errors.append(f"{recipe_dir.name}: allowed source needs rightsEvidence")

    outputs = recipe.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        errors.append(f"{recipe_dir.name}: outputs must be a non-empty list")
    else:
        for output in outputs:
            if not isinstance(output, dict):
                errors.append(f"{recipe_dir.name}: output entries must be mappings")
                continue
            output_path = output.get("path")
            if not isinstance(output_path, str) or not output_path.startswith(
                "output/"
            ):
                errors.append(f"{recipe_dir.name}: output path must start with output/")
            if output.get("publication") not in {"hosted", "local-only", "upstream"}:
                errors.append(f"{recipe_dir.name}: invalid output publication value")

    for metadata_name in ("sources.lock.json", "provenance.json"):
        try:
            json.loads((recipe_dir / metadata_name).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{recipe_dir.name}: invalid {metadata_name}: {error}")

    for script in sorted((recipe_dir / "scripts").glob("*.py")):
        script_text = script.read_text(encoding="utf-8")
        if "# /// script" not in script_text:
            errors.append(
                f"{recipe_dir.name}: missing PEP 723 metadata in {script.name}"
            )

    recipe_kind = recipe.get("kind")
    for spec in sorted((recipe_dir / "specs").glob("*.json")):
        try:
            value = json.loads(spec.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            errors.append(f"{recipe_dir.name}: invalid spec {spec.name}: {error}")
            continue
        errors.extend(check_spec_values(recipe_dir.name, spec.name, value, recipe_kind))

    consumers = recipe.get("consumers", [])
    if not isinstance(consumers, list):
        errors.append(f"{recipe_dir.name}: consumers must be a list")
    else:
        for consumer in consumers:
            if not isinstance(consumer, str) or not (recipe_dir / consumer).exists():
                errors.append(f"{recipe_dir.name}: missing consumer {consumer}")
    return errors


def walk_json(value: Any) -> Iterable[tuple[str, Any]]:
    """Yield every object key and value recursively."""

    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def check_spec_values(
    recipe_id: str, spec_name: str, value: Any, recipe_kind: Any
) -> list[str]:
    """Return errors for data URLs and embedded tables in a local spec."""

    errors: list[str] = []
    for key, child in walk_json(value):
        if key == "url" and isinstance(child, str):
            is_remote = child.startswith(("http://", "https://"))
            if is_remote and recipe_kind != "direct":
                errors.append(f"{recipe_id}: remote data URL in {spec_name}: {child}")
            elif not is_remote and not child.startswith("../output/"):
                errors.append(
                    f"{recipe_id}: non-output data URL in {spec_name}: {child}"
                )
        if key == "values" and isinstance(child, list) and child:
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
