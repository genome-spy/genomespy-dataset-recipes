#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0

# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "numpy==2.5.1",
#   "pybigwig==0.3.25",
# ]
# ///

"""Fetch and validate the original DynSeq SPI1 bQTL BigWigs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import pyBigWig  # type: ignore[import-not-found]

RECIPE_DIR = Path(__file__).resolve().parents[1]
PROVENANCE_PATH = RECIPE_DIR / "provenance.json"
OUTPUT_DIR = RECIPE_DIR / "output"
USER_AGENT = "GenomeSpy dataset recipe dynseq-spi1-bqtl"


@dataclass(frozen=True)
class SourceFile:
    """Identity and destination of one accepted BigWig."""

    role: str
    name: str
    url: str
    size: int
    md5: str
    sha256: str

    @property
    def output_path(self) -> Path:
        """Return the recipe-local output path."""

        return OUTPUT_DIR / self.name


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-directory",
        type=Path,
        help="Copy and validate accepted files from this directory.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify existing outputs without reading or downloading sources.",
    )
    return parser.parse_args()


def load_provenance() -> dict[str, Any]:
    """Load the committed accepted-run record."""

    value: Any = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("provenance.json must contain an object.")
    return value


def source_files(provenance: dict[str, Any]) -> list[SourceFile]:
    """Return and validate the two accepted source locks."""

    sources = provenance.get("sources")
    if not isinstance(sources, list) or len(sources) != 1:
        raise ValueError("Expected exactly one provenance source.")
    values = sources[0].get("files")
    if not isinstance(values, list):
        raise ValueError("Source files must be a list.")
    files = [
        SourceFile(
            role=str(value["role"]),
            name=Path(str(value["path"])).name,
            url=str(value["url"]),
            size=int(value["fileSizeBytes"]),
            md5=str(value["md5"]),
            sha256=str(value["sha256"]),
        )
        for value in values
    ]
    if {file.role for file in files} != {"reference", "alternate"}:
        raise ValueError("Expected one reference and one alternate source.")
    if len({file.name for file in files}) != len(files):
        raise ValueError("Accepted source filenames must be unique.")
    return files


def digest(path: Path, algorithm: str) -> str:
    """Return a streaming hexadecimal digest."""

    value = hashlib.new(algorithm)
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def validate_identity(path: Path, source: SourceFile) -> None:
    """Require a file to match its accepted byte identity."""

    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size != source.size:
        raise ValueError(f"File size does not match provenance: {path}")
    if digest(path, "md5") != source.md5:
        raise ValueError(f"MD5 does not match provenance: {path}")
    if digest(path, "sha256") != source.sha256:
        raise ValueError(f"SHA-256 does not match provenance: {path}")


def transfer(source: SourceFile, local_path: Path | None) -> None:
    """Copy or download one accepted file atomically."""

    destination = source.output_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    try:
        if local_path is None:
            request = Request(source.url, headers={"User-Agent": USER_AGENT})
            with urlopen(request) as response, temporary.open("wb") as output_file:
                shutil.copyfileobj(response, output_file)
        else:
            validate_identity(local_path, source)
            with (
                local_path.open("rb") as input_file,
                temporary.open("wb") as output_file,
            ):
                shutil.copyfileobj(input_file, output_file)
        validate_identity(temporary, source)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def prepare_outputs(files: list[SourceFile], directory: Path | None) -> None:
    """Populate missing outputs or copy explicit local sources."""

    source_directory = directory.expanduser().resolve() if directory else None
    for source in files:
        if source_directory is not None:
            transfer(source, source_directory / source.name)
        elif not source.output_path.exists():
            transfer(source, None)


def validate_bigwig(
    path: Path, source: SourceFile, provenance: dict[str, Any]
) -> tuple[list[tuple[int, int]], dict[str, float]]:
    """Validate one BigWig's assembly header, intervals, and scores."""

    parameters = provenance["parameters"]
    validation = provenance["validation"]
    interval = parameters["interval"]
    chrom = str(interval["chrom"])
    expected_start = int(interval["start"])
    expected_end = int(interval["end"])

    with pyBigWig.open(str(path)) as bigwig:
        chromosomes: dict[str, int] = bigwig.chroms()
        if len(chromosomes) != int(validation["chromosomeHeaderCount"]):
            raise ValueError(f"Unexpected chromosome-header count: {path}")
        if chromosomes.get(chrom) != int(validation["chr22Length"]):
            raise ValueError(f"Unexpected chr22 length: {path}")
        nonempty = [name for name in chromosomes if bigwig.intervals(name) is not None]
        if nonempty != validation["nonemptyChromosomes"]:
            raise ValueError(f"Unexpected non-empty chromosomes: {path}")
        records = list(bigwig.intervals(chrom) or [])

    if len(records) != int(validation["recordCountPerAllele"]):
        raise ValueError(f"Unexpected BigWig record count: {path}")
    coordinates = [(start, end) for start, end, _ in records]
    if not records or records[0][0] != expected_start or records[-1][1] != expected_end:
        raise ValueError(f"Unexpected BigWig interval extent: {path}")
    if any(end - start != 1 for start, end in coordinates):
        raise ValueError(f"BigWig intervals are not one base: {path}")
    if any(left[1] != right[0] for left, right in zip(coordinates, coordinates[1:])):
        raise ValueError(f"BigWig intervals are not contiguous: {path}")
    values = [float(value) for _, _, value in records]
    if any(not math.isfinite(value) for value in values):
        raise ValueError(f"BigWig contains a non-finite score: {path}")

    expected_range = validation["scoreRanges"][source.role]
    if min(values) != float(expected_range["minimum"]):
        raise ValueError(f"Minimum score does not match provenance: {path}")
    if max(values) != float(expected_range["maximum"]):
        raise ValueError(f"Maximum score does not match provenance: {path}")
    variant_position = int(parameters["variant"]["position"])
    variant_score = values[variant_position - expected_start]
    expected_score = float(validation["variantPositionScores"][source.role])
    if variant_score != expected_score:
        raise ValueError(f"Variant-position score does not match provenance: {path}")
    return coordinates, {"minimum": min(values), "maximum": max(values)}


def validate_outputs(files: list[SourceFile], provenance: dict[str, Any]) -> None:
    """Validate identities and require matched allele coordinates."""

    coordinates: dict[str, list[tuple[int, int]]] = {}
    for source in files:
        validate_identity(source.output_path, source)
        allele_coordinates, _ = validate_bigwig(source.output_path, source, provenance)
        coordinates[source.role] = allele_coordinates
    if coordinates["reference"] != coordinates["alternate"]:
        raise ValueError("Reference and alternate interval coordinates differ.")


def main() -> None:
    """Prepare or verify the accepted direct-source files."""

    args = parse_args()
    if args.verify_only and args.source_directory is not None:
        raise ValueError("--verify-only cannot be combined with --source-directory.")
    provenance = load_provenance()
    files = source_files(provenance)
    if not args.verify_only:
        prepare_outputs(files, args.source_directory)
    validate_outputs(files, provenance)
    action = "Verified" if args.verify_only else "Prepared and verified"
    print(f"{action} {len(files)} DynSeq SPI1 BigWigs.")


if __name__ == "__main__":
    main()
