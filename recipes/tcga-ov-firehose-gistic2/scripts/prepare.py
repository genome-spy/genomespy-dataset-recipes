#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0

# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""Verify and extract the accepted TCGA-OV Firehose GISTIC2 files."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import tarfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any
from urllib.request import Request, urlopen

RECIPE_DIR = Path(__file__).resolve().parents[1]
PROVENANCE_PATH = RECIPE_DIR / "provenance.json"
DOWNLOAD_DIR = RECIPE_DIR / "download"
OUTPUT_DIR = RECIPE_DIR / "output"
USER_AGENT = "GenomeSpy dataset recipe tcga-ov-firehose-gistic2"
SCORE_FIELDS = (
    "Type",
    "Chromosome",
    "Start",
    "End",
    "-log10(q-value)",
    "G-score",
    "average amplitude",
    "frequency",
)
LESION_FIELDS = (
    "Unique Name",
    "Descriptor",
    "Wide Peak Limits",
    "Peak Limits",
    "Region Limits",
    "q values",
    "Residual q values after removing segments shared with higher peaks",
    "Broad or Focal",
    "Amplitude Threshold",
)
LIMIT_PATTERN = re.compile(
    r"^chr(?:[1-9]|1[0-9]|2[0-2]|X):"
    r"(?P<start>[0-9]+)-(?P<end>[0-9]+)"
    r"\(probes (?P<probe_start>[0-9]+):(?P<probe_end>[0-9]+)\)\s*$"
)


@dataclass(frozen=True)
class LockedFile:
    """Identity of an accepted file."""

    name: str
    size: int
    md5: str
    sha256: str


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive",
        type=Path,
        help="Use this archive instead of the recipe download path.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify existing outputs without reading or downloading the archive.",
    )
    return parser.parse_args()


def load_provenance() -> dict[str, Any]:
    """Load the committed accepted-run record."""

    value: Any = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("provenance.json must contain an object.")
    return value


def source_record(provenance: dict[str, Any]) -> dict[str, Any]:
    """Return the sole accepted source record."""

    sources = provenance.get("sources")
    if not isinstance(sources, list) or len(sources) != 1:
        raise ValueError("Expected exactly one provenance source.")
    source = sources[0]
    if not isinstance(source, dict):
        raise ValueError("The provenance source must be an object.")
    return source


def locked_file(value: dict[str, Any]) -> LockedFile:
    """Parse one accepted file identity."""

    return LockedFile(
        name=str(value["name"]),
        size=int(value["fileSizeBytes"]),
        md5=str(value["md5"]),
        sha256=str(value["sha256"]),
    )


def digest(path: Path, algorithm: str) -> str:
    """Return a streaming hexadecimal digest."""

    value = hashlib.new(algorithm)
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def validate_identity(path: Path, lock: LockedFile) -> None:
    """Require a file to match its accepted identity."""

    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size != lock.size:
        raise ValueError(f"File size does not match provenance: {path}")
    if digest(path, "md5") != lock.md5:
        raise ValueError(f"MD5 does not match provenance: {path}")
    if digest(path, "sha256") != lock.sha256:
        raise ValueError(f"SHA-256 does not match provenance: {path}")


def download(url: str, destination: Path) -> None:
    """Download a file atomically."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request) as response, temporary.open("wb") as output_file:
            shutil.copyfileobj(response, output_file)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def resolve_archive(path: Path | None, source: dict[str, Any]) -> Path:
    """Resolve, optionally download, and verify the accepted archive."""

    default_path = DOWNLOAD_DIR / str(source["filename"])
    archive = (path or default_path).expanduser().resolve()
    if not archive.exists():
        if path is not None:
            raise FileNotFoundError(f"Explicit archive does not exist: {archive}")
        download(str(source["url"]), archive)
    lock = LockedFile(
        name=str(source["filename"]),
        size=int(source["fileSizeBytes"]),
        md5=str(source["md5"]),
        sha256=str(source["sha256"]),
    )
    validate_identity(archive, lock)
    return archive


def copy_member(input_file: IO[bytes], destination: Path) -> None:
    """Copy one archive member atomically."""

    temporary = destination.with_name(destination.name + ".part")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with temporary.open("wb") as output_file:
            shutil.copyfileobj(input_file, output_file)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def extract_outputs(
    archive: Path, source: dict[str, Any], locks: list[LockedFile]
) -> dict[str, Path]:
    """Extract only the accepted regular-file members."""

    prefix = str(source["archivePrefix"])
    absent = {prefix + str(name) for name in source["requiredAbsentMembers"]}
    output_paths: dict[str, Path] = {}
    with tarfile.open(archive, mode="r:gz") as tar:
        members = tar.getmembers()
        names = [member.name for member in members]
        if len(names) != int(load_provenance()["validation"]["archiveMemberCount"]):
            raise ValueError("Archive member count does not match provenance.")
        if absent.intersection(names):
            raise ValueError("An archive member required to be absent is present.")
        if len(names) != len(set(names)):
            raise ValueError("Archive contains duplicate member paths.")

        by_name = {member.name: member for member in members}
        for lock in locks:
            archive_name = prefix + lock.name
            member = by_name.get(archive_name)
            if member is None or not member.isfile():
                raise ValueError(
                    f"Missing accepted regular-file member: {archive_name}"
                )
            input_file = tar.extractfile(member)
            if input_file is None:
                raise ValueError(f"Cannot read accepted member: {archive_name}")
            destination = OUTPUT_DIR / lock.name
            with input_file:
                copy_member(input_file, destination)
            output_paths[lock.name] = destination
    return output_paths


def finite_float(value: str, label: str) -> float:
    """Parse one finite number."""

    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Non-finite {label}: {value}")
    return number


def validate_scores(path: Path, validation: dict[str, Any]) -> None:
    """Validate the accepted GISTIC score table."""

    counts: Counter[str] = Counter()
    chromosomes: set[int] = set()
    minimum_start: int | None = None
    maximum_end: int | None = None
    with path.open(encoding="utf-8", newline="") as input_file:
        reader = csv.reader(input_file, delimiter="\t")
        header = next(reader, None)
        if header != list(SCORE_FIELDS):
            raise ValueError("Unexpected scores.gistic header.")
        for line_number, row in enumerate(reader, start=2):
            if len(row) != len(SCORE_FIELDS):
                raise ValueError(f"Invalid scores.gistic row {line_number}.")
            event_type = row[0]
            if event_type not in {"Amp", "Del"}:
                raise ValueError(f"Invalid score type at row {line_number}.")
            chromosome = int(row[1])
            start, end = int(row[2]), int(row[3])
            if chromosome not in range(1, 24) or start < 1 or end < start:
                raise ValueError(f"Invalid score interval at row {line_number}.")
            for index, label in enumerate(SCORE_FIELDS[4:], start=4):
                finite_float(row[index], label)
            counts[event_type] += 1
            chromosomes.add(chromosome)
            minimum_start = (
                start if minimum_start is None else min(minimum_start, start)
            )
            maximum_end = end if maximum_end is None else max(maximum_end, end)

    expected_counts = validation["scoreTypeCounts"]
    if dict(counts) != expected_counts:
        raise ValueError("Score type counts do not match provenance.")
    if sorted(chromosomes) != validation["scoreChromosomes"]:
        raise ValueError("Score chromosomes do not match provenance.")
    expected_range = validation["scoreCoordinateRange"]
    if minimum_start != expected_range["minimumStart"]:
        raise ValueError("Minimum score coordinate does not match provenance.")
    if maximum_end != expected_range["maximumEnd"]:
        raise ValueError("Maximum score coordinate does not match provenance.")


def validate_lesions(path: Path, validation: dict[str, Any]) -> None:
    """Validate lesion types, source-format columns, and interval strings."""

    primary_counts: Counter[str] = Counter()
    cn_value_counts: Counter[str] = Counter()
    interval_count = 0
    minimum_start: int | None = None
    maximum_end: int | None = None
    with path.open(encoding="utf-8", newline="") as input_file:
        reader = csv.reader(input_file, delimiter="\t")
        header = next(reader, None)
        if header is None or header[: len(LESION_FIELDS)] != list(LESION_FIELDS):
            raise ValueError("Unexpected all-lesions header.")
        sample_fields = header[len(LESION_FIELDS) :]
        named_samples = [field for field in sample_fields if field]
        if len(named_samples) != validation["namedTumorSampleColumnCount"]:
            raise ValueError("Named sample-column count does not match provenance.")
        if len(named_samples) != len(set(named_samples)):
            raise ValueError("Duplicate named sample columns in all-lesions header.")
        if sample_fields.count("") != validation["trailingBlankSampleColumnCount"]:
            raise ValueError("Blank sample-column count does not match provenance.")
        if not sample_fields or sample_fields[-1] != "":
            raise ValueError("The accepted trailing blank sample column is missing.")

        for line_number, row in enumerate(reader, start=2):
            if len(row) != len(header):
                raise ValueError(f"Invalid all-lesions row {line_number}.")
            match = re.fullmatch(
                r"(Amplification|Deletion) Peak\s+\d+( - CN values)?", row[0]
            )
            if match is None:
                raise ValueError(f"Invalid lesion name at row {line_number}.")
            counts = cn_value_counts if match.group(2) else primary_counts
            counts[match.group(1)] += 1
            finite_float(row[5], "q value")
            finite_float(row[6], "residual q value")
            for value in row[2:5]:
                limit = LIMIT_PATTERN.fullmatch(value)
                if limit is None:
                    raise ValueError(f"Invalid lesion limits at row {line_number}.")
                start, end = int(limit["start"]), int(limit["end"])
                probe_start = int(limit["probe_start"])
                probe_end = int(limit["probe_end"])
                if start < 1 or end < start or probe_start > probe_end:
                    raise ValueError(f"Reversed lesion interval at row {line_number}.")
                interval_count += 1
                minimum_start = (
                    start if minimum_start is None else min(minimum_start, start)
                )
                maximum_end = end if maximum_end is None else max(maximum_end, end)

    if dict(primary_counts) != validation["primaryLesionCounts"]:
        raise ValueError("Primary lesion counts do not match provenance.")
    if dict(cn_value_counts) != validation["cnValueRowCounts"]:
        raise ValueError("CN-value row counts do not match provenance.")
    if interval_count != validation["parsedLesionIntervalCount"]:
        raise ValueError("Lesion interval count does not match provenance.")
    expected_range = validation["lesionCoordinateRange"]
    if minimum_start != expected_range["minimumStart"]:
        raise ValueError("Minimum lesion coordinate does not match provenance.")
    if maximum_end != expected_range["maximumEnd"]:
        raise ValueError("Maximum lesion coordinate does not match provenance.")


def validate_outputs(
    paths: dict[str, Path], locks: list[LockedFile], validation: dict[str, Any]
) -> None:
    """Validate output identities and scientific structure."""

    by_name = {lock.name: lock for lock in locks}
    for name, lock in by_name.items():
        validate_identity(paths[name], lock)
    validate_scores(paths["scores.gistic"], validation)
    validate_lesions(paths["all_lesions.conf_99.txt"], validation)


def main() -> None:
    """Prepare or verify the accepted outputs."""

    args = parse_args()
    provenance = load_provenance()
    source = source_record(provenance)
    locks = [locked_file(value) for value in source["acceptedMembers"]]
    if {lock.name for lock in locks} != {
        "scores.gistic",
        "all_lesions.conf_99.txt",
    }:
        raise ValueError("Unexpected accepted member set in provenance.")

    paths = {lock.name: OUTPUT_DIR / lock.name for lock in locks}
    if not args.verify_only:
        archive = resolve_archive(args.archive, source)
        paths = extract_outputs(archive, source, locks)
    validate_outputs(paths, locks, provenance["validation"])
    action = "Verified" if args.verify_only else "Prepared and verified"
    print(f"{action} {len(paths)} TCGA-OV GISTIC2 outputs.")


if __name__ == "__main__":
    main()
