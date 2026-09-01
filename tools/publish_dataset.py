#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///
"""Inspect or publish rights-cleared recipe artifacts in Amazon S3."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RECIPES_DIR = ROOT / "recipes"
SHARED_DATA_ROOT = ROOT.parent / "example-dataset-wrangling"
DECISION_HEADING = re.compile(r"^##[ \t]+Decision[ \t]*$", re.MULTILINE)
NEXT_HEADING = re.compile(r"^#{1,6}[ \t]+", re.MULTILINE)
ELIGIBLE_DECISION = re.compile(
    r"^Eligible for GenomeSpy-managed hosting(?:\.| under(?:\s|$))", re.IGNORECASE
)
SHA256 = re.compile(r"^[0-9a-f]{64}$")
RECIPE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RELEASE_ID = re.compile(r"^v[1-9][0-9]*$")
PUT_OBJECT_LIMIT = 5_000_000_000
CACHE_CONTROL = "public,max-age=31536000,immutable"
DEFAULT_CORS_ORIGIN = "https://genomespy.app"
DEFAULT_CONFIG_PATH = ROOT / ".genomespy-publish.toml"
CONFIG_KEYS = {"default_target", "targets"}
TARGET_KEYS = {
    "allow_source_roots",
    "bucket",
    "cors_origin",
    "expected_bucket_owner",
    "profile",
    "region",
    "skip_public_verification",
}


class PublicationError(RuntimeError):
    """A publication precondition or verification failure."""


@dataclass(frozen=True)
class Artifact:
    """One local file and its immutable hosted identity."""

    relative_path: str
    local_path: Path
    key: str
    public_url: str
    file_size_bytes: int
    sha256: str
    content_type: str
    is_data: bool = True


@dataclass(frozen=True)
class Release:
    """A fully resolved release selected by the caller."""

    recipe_id: str
    release_id: str
    recipe_dir: Path
    base_url: str
    git_commit: str
    artifacts: tuple[Artifact, ...]


@dataclass(frozen=True)
class RemoteState:
    """Comparison of an expected artifact with S3."""

    status: str
    detail: str = ""


def load_config(path: Path) -> dict[str, Any]:
    """Load and validate an optional local publication configuration."""

    if not path.exists():
        return {}
    try:
        with path.open("rb") as stream:
            value: Any = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise PublicationError(
            f"cannot read publication config {path}: {error}"
        ) from error
    if not isinstance(value, dict):
        raise PublicationError(f"publication config {path} must be a TOML table")
    unknown = set(value) - CONFIG_KEYS
    if unknown:
        raise PublicationError(f"unknown publication config key: {sorted(unknown)[0]}")
    default_target = value.get("default_target")
    if default_target is not None and not isinstance(default_target, str):
        raise PublicationError("publication config default_target must be a string")
    targets = value.get("targets", {})
    if not isinstance(targets, dict):
        raise PublicationError("publication config targets must be a table")
    for name, target in targets.items():
        if not isinstance(name, str) or not isinstance(target, dict):
            raise PublicationError("each publication target must be a TOML table")
        target_unknown = set(target) - TARGET_KEYS
        if target_unknown:
            raise PublicationError(
                f"unknown key in publication target {name}: {sorted(target_unknown)[0]}"
            )
        for key in (
            "bucket",
            "profile",
            "region",
            "expected_bucket_owner",
            "cors_origin",
        ):
            if key in target and not isinstance(target[key], str):
                raise PublicationError(
                    f"publication target {name}.{key} must be a string"
                )
        if "skip_public_verification" in target and not isinstance(
            target["skip_public_verification"], bool
        ):
            raise PublicationError(
                f"publication target {name}.skip_public_verification must be boolean"
            )
        roots = target.get("allow_source_roots", [])
        if not isinstance(roots, list) or not all(
            isinstance(root, str) for root in roots
        ):
            raise PublicationError(
                f"publication target {name}.allow_source_roots must be an array "
                "of strings"
            )
    if default_target is not None and default_target not in targets:
        raise PublicationError(
            f"publication config default target does not exist: {default_target}"
        )
    return value


def target_or_environment(
    target: dict[str, Any], key: str, *environment_names: str
) -> Any:
    """Prefer a selected target over environment fallbacks."""

    if key in target:
        return target[key]
    for name in environment_names:
        if name in os.environ:
            return os.environ[name]
    return None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse a deliberately opt-in publication command."""

    arguments = sys.argv[1:] if argv is None else argv
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    bootstrap.add_argument(
        "--target", default=os.environ.get("GENOMESPY_PUBLISH_TARGET")
    )
    preliminary, _ = bootstrap.parse_known_args(arguments)
    try:
        config = load_config(preliminary.config)
    except PublicationError as error:
        bootstrap.error(str(error))
    target_name = preliminary.target or config.get("default_target")
    targets = config.get("targets", {})
    if target_name is not None and target_name not in targets:
        bootstrap.error(f"unknown publication target: {target_name}")
    target = targets.get(target_name, {})

    parser = argparse.ArgumentParser(
        description=(
            "Inspect hosted recipe artifacts, or explicitly plan, publish, and "
            "verify selected releases."
        )
    )
    parser.add_argument("action", choices=("status", "plan", "publish", "verify"))
    parser.add_argument(
        "recipes",
        nargs="*",
        metavar="RECIPE_ID",
        help=(
            "recipe IDs; status checks all publishable recipes when omitted, "
            "but write-capable actions always require explicit IDs"
        ),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=preliminary.config,
        help=f"local target configuration (default: {DEFAULT_CONFIG_PATH.name})",
    )
    parser.add_argument(
        "--target",
        default=target_name,
        help="named target from the local publication configuration",
    )
    parser.add_argument(
        "--bucket",
        default=target_or_environment(target, "bucket", "GENOMESPY_DATA_BUCKET"),
        help="S3 bucket (overrides the selected target)",
    )
    parser.add_argument(
        "--profile",
        default=target_or_environment(target, "profile", "AWS_PROFILE"),
        help="AWS named profile (overrides the selected target)",
    )
    parser.add_argument(
        "--region",
        default=target_or_environment(
            target, "region", "AWS_REGION", "AWS_DEFAULT_REGION"
        ),
        help="AWS region (overrides the selected target)",
    )
    parser.add_argument(
        "--expected-bucket-owner",
        default=target_or_environment(
            target, "expected_bucket_owner", "GENOMESPY_DATA_BUCKET_OWNER"
        ),
        help="AWS account ID expected to own the bucket (overrides the target)",
    )
    parser.add_argument(
        "--allow-source-root",
        action="append",
        default=[Path(root) for root in target.get("allow_source_roots", [])],
        type=Path,
        metavar="PATH",
        help=(
            "allow artifact symlinks to resolve under PATH; repeat for additional "
            "local source roots"
        ),
    )
    parser.add_argument(
        "--skip-public-verification",
        action=argparse.BooleanOptionalAction,
        default=target.get("skip_public_verification", False),
        help="verify S3 only, without checking the CloudFront URLs (target-aware)",
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="download public data objects and verify their SHA-256 checksums",
    )
    parser.add_argument(
        "--cors-origin",
        default=target.get("cors_origin", DEFAULT_CORS_ORIGIN),
        help=f"Origin header used for CORS checks (default: {DEFAULT_CORS_ORIGIN})",
    )
    args = parser.parse_args(arguments)
    if args.action != "status" and not args.recipes:
        parser.error(f"{args.action} requires at least one explicit recipe ID")
    if not args.bucket:
        parser.error(
            "no bucket configured; use --bucket, GENOMESPY_DATA_BUCKET, or a target"
        )
    return args


def run(
    command: list[str],
    *,
    check: bool = True,
    cwd: Path = ROOT,
) -> subprocess.CompletedProcess[str]:
    """Run a command and retain its text output for precise failures."""

    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise PublicationError(f"Could not run {command[0]}: {error}") from error
    if check and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise PublicationError(f"Command failed: {' '.join(command)}\n{message}")
    return result


class AwsCli:
    """Small JSON-oriented adapter around the installed AWS CLI."""

    def __init__(
        self,
        profile: str | None,
        region: str | None,
        expected_bucket_owner: str | None,
    ) -> None:
        self.profile = profile
        self.region = region
        self.expected_bucket_owner = expected_bucket_owner

    def command(self, *arguments: str) -> list[str]:
        """Build an AWS CLI command using the selected local profile."""

        command = ["aws", *arguments, "--output", "json", "--no-cli-pager"]
        if self.profile:
            command.extend(("--profile", self.profile))
        if self.region:
            command.extend(("--region", self.region))
        return command

    def call(
        self, *arguments: str, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        """Run one AWS operation."""

        return run(self.command(*arguments), check=check)

    def json(self, *arguments: str) -> dict[str, Any]:
        """Run one AWS operation and decode its JSON object response."""

        result = self.call(*arguments)
        try:
            value: Any = json.loads(result.stdout or "{}")
        except json.JSONDecodeError as error:
            raise PublicationError(f"AWS CLI returned invalid JSON: {error}") from error
        if not isinstance(value, dict):
            raise PublicationError("AWS CLI returned a non-object JSON response")
        return value

    def owner_arguments(self) -> tuple[str, ...]:
        """Return the bucket-owner guard when configured."""

        if self.expected_bucket_owner:
            return ("--expected-bucket-owner", self.expected_bucket_owner)
        return ()


def digest(path: Path) -> str:
    """Return the SHA-256 fingerprint of a file, following recipe symlinks."""

    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def content_type(path: str) -> str:
    """Return stable content types suitable for GenomeSpy data loading."""

    lowered = path.lower()
    if lowered.endswith(".json"):
        return "application/json"
    if lowered.endswith(".md"):
        return "text/markdown; charset=utf-8"
    if lowered.endswith(".tsv"):
        return "text/tab-separated-values; charset=utf-8"
    if lowered.endswith((".txt", ".vcf", ".gistic")):
        return "text/plain; charset=utf-8"
    if lowered.endswith(".gz"):
        return "application/gzip"
    return "application/octet-stream"


def git_value(*arguments: str) -> str:
    """Return a single Git value from this repository."""

    return run(["git", *arguments]).stdout.strip()


def repository_url() -> str:
    """Normalize the origin remote into a browsable repository URL."""

    remote = git_value("remote", "get-url", "origin")
    if remote.startswith("git@github.com:"):
        remote = "https://github.com/" + remote.removeprefix("git@github.com:")
    elif remote.startswith("ssh://git@github.com/"):
        remote = "https://github.com/" + remote.removeprefix("ssh://git@github.com/")
    return remote.removesuffix(".git")


def hosting_is_eligible(rights: str) -> bool:
    """Return whether the Decision section starts with the hosting decision."""

    headings = list(DECISION_HEADING.finditer(rights))
    if len(headings) != 1:
        return False
    section = rights[headings[0].end() :]
    next_heading = NEXT_HEADING.search(section)
    if next_heading:
        section = section[: next_heading.start()]
    return ELIGIBLE_DECISION.match(section.lstrip()) is not None


def require_committed_recipe(recipe_dir: Path) -> str:
    """Require a clean recipe and return its stable source commit."""

    relative = recipe_dir.relative_to(ROOT)
    required_files = [
        relative / "README.md",
        relative / "RIGHTS.md",
        relative / "provenance.json",
    ]
    result = run(
        ["git", "diff", "--quiet", "HEAD", "--", str(relative)],
        check=False,
    )
    untracked = run(
        [
            "git",
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            str(relative),
        ]
    ).stdout.strip()
    if result.returncode != 0 or untracked:
        raise PublicationError(
            f"{recipe_dir.name}: the complete recipe source must be committed "
            "before publication"
        )
    for path in required_files:
        run(["git", "ls-files", "--error-unmatch", str(path)])
    commit = git_value("log", "-1", "--format=%H", "--", str(relative))
    if not commit:
        raise PublicationError(f"{recipe_dir.name}: recipe has no committed source")
    return commit


def validate_artifact_path(value: str) -> PurePosixPath:
    """Validate one manifest path without resolving ignored local symlinks."""

    path = PurePosixPath(value)
    if path.as_posix() != value:
        raise PublicationError(f"non-canonical publication artifact path: {value}")
    if path.is_absolute() or not path.parts or path.parts[0] != "output":
        raise PublicationError(f"invalid publication artifact path: {value}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise PublicationError(f"unsafe publication artifact path: {value}")
    if len(path.parts) == 1:
        raise PublicationError(f"publication artifact must name a file: {value}")
    return path


def validate_artifact_source(
    local_path: Path,
    recipe_dir: Path,
    allowed_source_roots: Sequence[Path],
) -> Path:
    """Resolve an artifact and constrain external symlinks to trusted roots."""

    try:
        resolved = local_path.resolve(strict=True)
    except OSError as error:
        raise PublicationError(
            f"cannot resolve local artifact {local_path}: {error}"
        ) from error
    if not resolved.is_file():
        raise PublicationError(f"local artifact is not a regular file: {local_path}")
    roots = (recipe_dir.resolve(), SHARED_DATA_ROOT.resolve(), *allowed_source_roots)
    if not any(resolved.is_relative_to(root.resolve()) for root in roots):
        raise PublicationError(
            f"{local_path.relative_to(recipe_dir)} resolves outside the trusted "
            f"artifact roots: {resolved}; pass --allow-source-root {resolved.parent}"
        )
    return resolved


def release_prefix(base_url: str, recipe_id: str, release_id: str) -> str:
    """Validate a canonical public base URL and return its S3 key prefix."""

    if not RECIPE_ID.fullmatch(recipe_id):
        raise PublicationError(f"invalid recipe ID: {recipe_id}")
    if not RELEASE_ID.fullmatch(release_id):
        raise PublicationError(f"invalid release ID: {release_id}")
    parsed = urlparse(base_url)
    expected_path = f"/datasets/{recipe_id}/{release_id}/"
    if (
        parsed.scheme != "https"
        or parsed.netloc != "data.genomespy.app"
        or parsed.path != expected_path
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise PublicationError(f"invalid distribution baseUrl: {base_url}")
    return expected_path.lstrip("/")


def load_release(
    recipe_id: str,
    *,
    validate_local: bool = True,
    require_commit: bool = True,
    allowed_source_roots: Sequence[Path] = (),
) -> Release:
    """Load one release, optionally enforcing local publication preconditions."""

    if not RECIPE_ID.fullmatch(recipe_id):
        raise PublicationError(f"invalid recipe ID: {recipe_id}")
    recipe_dir = RECIPES_DIR / recipe_id
    if recipe_id == "_template" or not recipe_dir.is_dir():
        raise PublicationError(f"unknown recipe: {recipe_id}")
    provenance_path = recipe_dir / "provenance.json"
    rights_path = recipe_dir / "RIGHTS.md"
    try:
        provenance: Any = json.loads(provenance_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PublicationError(
            f"{recipe_id}: invalid provenance.json: {error}"
        ) from error
    if not isinstance(provenance, dict) or provenance.get("recipeId") != recipe_id:
        raise PublicationError(f"{recipe_id}: provenance recipe ID does not match")
    if provenance.get("schemaVersion") != 2:
        raise PublicationError(
            f"{recipe_id}: publication requires provenance schemaVersion 2"
        )
    release_id = provenance.get("releaseId")
    if not isinstance(release_id, str) or not RELEASE_ID.fullmatch(release_id):
        raise PublicationError(f"{recipe_id}: invalid releaseId")
    distribution = provenance.get("distribution")
    if not isinstance(distribution, dict):
        raise PublicationError(
            f"{recipe_id}: no distribution is proposed; nothing can be published"
        )
    base_url = distribution.get("baseUrl")
    if not isinstance(base_url, str):
        raise PublicationError(f"{recipe_id}: distribution.baseUrl is missing")
    prefix = release_prefix(base_url, recipe_id, release_id)
    try:
        rights = rights_path.read_text(encoding="utf-8")
    except OSError as error:
        raise PublicationError(
            f"{recipe_id}: cannot read RIGHTS.md: {error}"
        ) from error
    if not hosting_is_eligible(rights):
        raise PublicationError(
            f"{recipe_id}: the RIGHTS.md Decision section does not start with the "
            "exact eligible-for-hosting decision"
        )
    manifest = distribution.get("artifacts")
    if not isinstance(manifest, dict) or not manifest:
        raise PublicationError(f"{recipe_id}: distribution.artifacts is missing")

    artifacts: list[Artifact] = []
    seen_keys: set[str] = set()
    for relative_text, identity in manifest.items():
        if not isinstance(relative_text, str) or not isinstance(identity, dict):
            raise PublicationError(f"{recipe_id}: invalid artifact manifest entry")
        relative = validate_artifact_path(relative_text)
        size = identity.get("fileSizeBytes")
        sha256 = identity.get("sha256")
        if type(size) is not int or size < 0:
            raise PublicationError(f"{recipe_id}: invalid size for {relative_text}")
        if not isinstance(sha256, str) or not SHA256.fullmatch(sha256):
            raise PublicationError(f"{recipe_id}: invalid SHA-256 for {relative_text}")
        local_path = recipe_dir.joinpath(*relative.parts)
        source_path = local_path
        if validate_local:
            resolved_path = validate_artifact_source(
                local_path, recipe_dir, allowed_source_roots
            )
            source_path = resolved_path
            actual_size = resolved_path.stat().st_size
            if actual_size != size:
                raise PublicationError(
                    f"{recipe_id}: size changed for {relative_text}: "
                    f"{actual_size} != {size}"
                )
            actual_sha256 = digest(resolved_path)
            if actual_sha256 != sha256:
                raise PublicationError(
                    f"{recipe_id}: SHA-256 changed for {relative_text}"
                )
        artifact_path = PurePosixPath(*relative.parts[1:]).as_posix()
        key = prefix + artifact_path
        if key in seen_keys:
            raise PublicationError(f"{recipe_id}: duplicate hosted key {key}")
        seen_keys.add(key)
        artifacts.append(
            Artifact(
                relative_path=relative_text,
                local_path=source_path,
                key=key,
                public_url=urljoin(base_url, artifact_path),
                file_size_bytes=size,
                sha256=sha256,
                content_type=content_type(relative_text),
            )
        )

    commit = require_committed_recipe(recipe_dir) if require_commit else ""
    return Release(
        recipe_id=recipe_id,
        release_id=release_id,
        recipe_dir=recipe_dir,
        base_url=base_url,
        git_commit=commit,
        artifacts=tuple(artifacts),
    )


def discover_publishable_recipes() -> list[str]:
    """Find recipes that declare an artifact inventory for managed hosting."""

    recipe_ids: list[str] = []
    for provenance_path in sorted(RECIPES_DIR.glob("*/provenance.json")):
        if provenance_path.parent.name == "_template":
            continue
        try:
            value: Any = json.loads(provenance_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(value, dict) or value.get("schemaVersion") != 2:
            continue
        distribution = value.get("distribution")
        if (
            isinstance(distribution, dict)
            and isinstance(distribution.get("baseUrl"), str)
            and isinstance(distribution.get("artifacts"), dict)
            and distribution["artifacts"]
        ):
            recipe_ids.append(provenance_path.parent.name)
    return recipe_ids


def release_readme(release: Release, rights: str) -> str:
    """Render the public release description and required rights conditions."""

    source_url = (
        f"{repository_url()}/tree/{release.git_commit}/recipes/{release.recipe_id}/"
    )
    return (
        f"# {release.recipe_id} {release.release_id}\n\n"
        "This directory contains the versioned data artifacts produced or selected "
        f"by the `{release.recipe_id}` GenomeSpy dataset recipe.\n\n"
        f"Exact recipe source: [{release.git_commit}]({source_url})\n\n"
        "> The recipe repository's CC0 dedication does not license the data files "
        "in this directory. The redistribution evidence and conditions below apply.\n\n"
        f"{rights.strip()}\n"
    )


def stage_sidecars(release: Release, directory: Path) -> tuple[Artifact, Artifact]:
    """Create deterministic release sidecars in a temporary directory."""

    rights = (release.recipe_dir / "RIGHTS.md").read_text(encoding="utf-8")
    readme_path = directory / "README.md"
    readme_path.write_text(release_readme(release, rights), encoding="utf-8")
    provenance_path = release.recipe_dir / "provenance.json"
    prefix = release_prefix(release.base_url, release.recipe_id, release.release_id)
    sidecars: list[Artifact] = []
    for name, path in (
        ("README.md", readme_path),
        ("provenance.json", provenance_path),
    ):
        sidecars.append(
            Artifact(
                relative_path=name,
                local_path=path,
                key=prefix + name,
                public_url=urljoin(release.base_url, name),
                file_size_bytes=path.stat().st_size,
                sha256=digest(path),
                content_type=content_type(name),
                is_data=False,
            )
        )
    return sidecars[0], sidecars[1]


def head_object(aws: AwsCli, bucket: str, key: str) -> dict[str, Any] | None:
    """Return S3 object metadata, distinguishing absence from denied access."""

    result = aws.call(
        "s3api",
        "head-object",
        "--bucket",
        bucket,
        "--key",
        key,
        *aws.owner_arguments(),
        check=False,
    )
    if result.returncode == 0:
        try:
            value: Any = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise PublicationError(f"invalid HeadObject response for {key}") from error
        if not isinstance(value, dict):
            raise PublicationError(f"invalid HeadObject response for {key}")
        return value
    message = result.stderr
    if "404" in message or "Not Found" in message or "NoSuchKey" in message:
        return None
    raise PublicationError(f"cannot inspect s3://{bucket}/{key}: {message.strip()}")


def compare_remote(head: dict[str, Any] | None, artifact: Artifact) -> RemoteState:
    """Compare S3 metadata with one expected immutable object."""

    if head is None:
        return RemoteState("missing")
    metadata = head.get("Metadata")
    actual_sha256 = metadata.get("sha256") if isinstance(metadata, dict) else None
    differences: list[str] = []
    if head.get("ContentLength") != artifact.file_size_bytes:
        differences.append("size")
    if actual_sha256 != artifact.sha256:
        differences.append("sha256 metadata")
    if head.get("ContentType") != artifact.content_type:
        differences.append("content type")
    if head.get("CacheControl") != CACHE_CONTROL:
        differences.append("cache control")
    if differences:
        return RemoteState("conflict", ", ".join(differences))
    return RemoteState("matching")


def put_object_arguments(
    aws: AwsCli,
    bucket: str,
    release: Release,
    artifact: Artifact,
) -> list[str]:
    """Build a conditional, checksummed immutable PutObject operation."""

    checksum = base64.b64encode(bytes.fromhex(artifact.sha256)).decode("ascii")
    metadata = ",".join(
        (
            f"sha256={artifact.sha256}",
            f"recipe-id={release.recipe_id}",
            f"release-id={release.release_id}",
            f"recipe-commit={release.git_commit}",
        )
    )
    return aws.command(
        "s3api",
        "put-object",
        "--bucket",
        bucket,
        "--key",
        artifact.key,
        "--body",
        str(artifact.local_path),
        "--content-type",
        artifact.content_type,
        "--cache-control",
        CACHE_CONTROL,
        "--metadata",
        metadata,
        "--checksum-sha256",
        checksum,
        "--if-none-match",
        "*",
        *aws.owner_arguments(),
    )


def upload_object(
    aws: AwsCli,
    bucket: str,
    release: Release,
    artifact: Artifact,
) -> None:
    """Upload one absent object without ever replacing an existing key."""

    if artifact.file_size_bytes > PUT_OBJECT_LIMIT:
        raise PublicationError(
            f"{artifact.relative_path} exceeds S3's 5 GB single-PUT limit"
        )
    result = run(put_object_arguments(aws, bucket, release, artifact), check=False)
    if result.returncode == 0:
        return
    # A concurrent publisher may have won the conditional write. Accept it only
    # after comparing the resulting immutable object with our manifest.
    state = compare_remote(head_object(aws, bucket, artifact.key), artifact)
    if state.status == "matching":
        return
    message = result.stderr.strip() or result.stdout.strip()
    raise PublicationError(f"upload failed for {artifact.key}: {message}")


def verify_public_range(artifact: Artifact, cors_origin: str) -> None:
    """Verify public availability, byte ranges, type, and CORS."""

    request = Request(
        artifact.public_url,
        headers={"Range": "bytes=0-0", "Origin": cors_origin},
    )
    try:
        with urlopen(request, timeout=60) as response:
            status = response.status
            response.read(1)
            headers = response.headers
    except (HTTPError, URLError, TimeoutError) as error:
        raise PublicationError(
            f"public request failed: {artifact.public_url}: {error}"
        ) from error
    if artifact.file_size_bytes > 1 and status != 206:
        raise PublicationError(
            f"public range request returned HTTP {status}: {artifact.public_url}"
        )
    if headers.get_content_type() != artifact.content_type.split(";", 1)[0]:
        raise PublicationError(f"public content type differs: {artifact.public_url}")
    allowed_origin = headers.get("Access-Control-Allow-Origin")
    if allowed_origin not in {"*", cors_origin}:
        raise PublicationError(f"public CORS header is missing: {artifact.public_url}")


def verify_public_checksum(artifact: Artifact) -> None:
    """Download one public object and verify its canonical SHA-256."""

    value = hashlib.sha256()
    try:
        with urlopen(artifact.public_url, timeout=60) as response:
            for chunk in iter(lambda: response.read(1024 * 1024), b""):
                value.update(chunk)
    except (HTTPError, URLError, TimeoutError) as error:
        raise PublicationError(
            f"public download failed: {artifact.public_url}: {error}"
        ) from error
    if value.hexdigest() != artifact.sha256:
        raise PublicationError(f"public checksum differs: {artifact.public_url}")


def verify_public(
    artifacts: tuple[Artifact, ...],
    *,
    cors_origin: str,
    deep: bool,
) -> None:
    """Verify CloudFront behavior and optionally re-download all data."""

    for artifact in artifacts:
        verify_public_range(artifact, cors_origin)
        if deep and artifact.is_data:
            verify_public_checksum(artifact)


def print_identity(aws: AwsCli) -> None:
    """Show the AWS principal before reading or writing the selected bucket."""

    identity = aws.json("sts", "get-caller-identity")
    print(f"AWS account: {identity.get('Account', '?')}")
    print(f"AWS principal: {identity.get('Arn', '?')}")


def print_external_sources(release: Release) -> None:
    """Summarize manifest-matched artifacts resolved outside the recipe."""

    recipe_root = release.recipe_dir.resolve()
    external = [
        artifact.local_path
        for artifact in release.artifacts
        if not artifact.local_path.is_relative_to(recipe_root)
    ]
    if not external:
        return
    common_parent = Path(os.path.commonpath([str(path.parent) for path in external]))
    print(
        f"{release.recipe_id}/{release.release_id}: {len(external)} artifacts "
        f"resolve from trusted external source {common_parent}"
    )


def list_release_objects(aws: AwsCli, bucket: str, prefix: str) -> dict[str, int]:
    """List object sizes under one immutable release prefix."""

    objects: dict[str, int] = {}
    continuation_token: str | None = None
    while True:
        arguments = [
            "s3api",
            "list-objects-v2",
            "--bucket",
            bucket,
            "--prefix",
            prefix,
            *aws.owner_arguments(),
        ]
        if continuation_token is not None:
            arguments.extend(("--continuation-token", continuation_token))
        response = aws.json(*arguments)
        contents = response.get("Contents", [])
        if not isinstance(contents, list):
            raise PublicationError(f"invalid ListObjectsV2 response for {prefix}")
        for value in contents:
            if not isinstance(value, dict):
                raise PublicationError(f"invalid ListObjectsV2 response for {prefix}")
            key = value.get("Key")
            size = value.get("Size")
            if not isinstance(key, str) or not isinstance(size, int):
                raise PublicationError(f"invalid ListObjectsV2 response for {prefix}")
            objects[key] = size
        if not response.get("IsTruncated", False):
            break
        continuation_token = response.get("NextContinuationToken")
        if not isinstance(continuation_token, str) or not continuation_token:
            raise PublicationError(f"invalid ListObjectsV2 pagination for {prefix}")
    return objects


def print_release_status(release: Release, aws: AwsCli, bucket: str) -> bool:
    """Report whether each declared data artifact exists with its expected size."""

    prefix = release_prefix(release.base_url, release.recipe_id, release.release_id)
    remote = list_release_objects(aws, bucket, prefix)
    missing = [artifact for artifact in release.artifacts if artifact.key not in remote]
    size_conflicts = [
        artifact
        for artifact in release.artifacts
        if artifact.key in remote and remote[artifact.key] != artifact.file_size_bytes
    ]
    present = len(release.artifacts) - len(missing) - len(size_conflicts)
    print(
        f"{release.recipe_id}/{release.release_id}: "
        f"{present}/{len(release.artifacts)} artifacts match S3, "
        f"{len(missing)} missing, {len(size_conflicts)} size conflicts"
    )
    for artifact in missing:
        print(f"  missing: {artifact.relative_path} -> s3://{bucket}/{artifact.key}")
    for artifact in size_conflicts:
        print(
            f"  size conflict: {artifact.relative_path} "
            f"(expected {artifact.file_size_bytes}, found {remote[artifact.key]}) -> "
            f"s3://{bucket}/{artifact.key}"
        )
    return not missing and not size_conflicts


def process_release(
    action: str,
    release: Release,
    artifacts: tuple[Artifact, ...],
    aws: AwsCli,
    bucket: str,
) -> None:
    """Plan, publish, or verify one selected release."""

    states = {
        artifact.key: compare_remote(head_object(aws, bucket, artifact.key), artifact)
        for artifact in artifacts
    }
    missing = [
        artifact for artifact in artifacts if states[artifact.key].status == "missing"
    ]
    conflicts = [
        artifact for artifact in artifacts if states[artifact.key].status == "conflict"
    ]
    matching = len(artifacts) - len(missing) - len(conflicts)
    print(
        f"{release.recipe_id}/{release.release_id}: "
        f"{matching} matching, {len(missing)} missing, {len(conflicts)} conflicting"
    )
    for artifact in missing:
        print(f"  missing: s3://{bucket}/{artifact.key}")
    for artifact in conflicts:
        print(
            f"  conflict: s3://{bucket}/{artifact.key} ({states[artifact.key].detail})"
        )
    if conflicts:
        raise PublicationError(
            f"{release.recipe_id}: immutable release contains conflicting objects"
        )
    if action == "verify" and missing:
        raise PublicationError(f"{release.recipe_id}: release is incomplete")
    if action == "publish":
        for artifact in missing:
            print(f"  uploading: {artifact.relative_path}")
            upload_object(aws, bucket, release, artifact)
        for artifact in artifacts:
            state = compare_remote(head_object(aws, bucket, artifact.key), artifact)
            if state.status != "matching":
                raise PublicationError(
                    f"post-upload verification failed for s3://{bucket}/{artifact.key}"
                )


def main(argv: list[str] | None = None) -> int:
    """Inspect inventory, or publish only explicitly selected releases."""

    args = parse_args(argv)
    aws = AwsCli(args.profile, args.region, args.expected_bucket_owner)
    try:
        run(["aws", "--version"])
        recipe_ids = args.recipes
        if args.action == "status" and not recipe_ids:
            recipe_ids = discover_publishable_recipes()
        if not recipe_ids:
            raise PublicationError("no publishable recipe artifact inventories found")
        releases = [
            load_release(
                recipe_id,
                validate_local=args.action != "status",
                require_commit=args.action != "status",
                allowed_source_roots=args.allow_source_root,
            )
            for recipe_id in recipe_ids
        ]
        if args.action != "status":
            for release in releases:
                print_external_sources(release)
        target_label = f" ({args.target})" if args.target else ""
        print(f"S3 destination{target_label}: s3://{args.bucket}")
        print_identity(aws)
        if args.action == "status":
            for release in releases:
                print_release_status(release, aws, args.bucket)
            return 0
        with tempfile.TemporaryDirectory(prefix="genomespy-publication-") as temporary:
            staging_dir = Path(temporary)
            for release in releases:
                sidecar_dir = staging_dir / release.recipe_id
                sidecar_dir.mkdir(parents=True, exist_ok=True)
                sidecars = stage_sidecars(release, sidecar_dir)
                artifacts = (*release.artifacts, *sidecars)
                process_release(args.action, release, artifacts, aws, args.bucket)
                if (
                    args.action in {"publish", "verify"}
                    and not args.skip_public_verification
                ):
                    verify_public(
                        artifacts,
                        cors_origin=args.cors_origin,
                        deep=args.deep,
                    )
                    print(
                        f"{release.recipe_id}/{release.release_id}: "
                        "public URLs verified"
                    )
        return 0
    except PublicationError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
