#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0

# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "numpy==2.5.1",
#   "pybigwig==0.3.25",
# ]
# ///

"""Prepare and validate the pinned ENCODE ATAC BigWig fixture."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
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
DOWNLOAD_DIR = RECIPE_DIR / "download"
WORK_DIR = RECIPE_DIR / "work"
OUTPUT_DIR = RECIPE_DIR / "output"
BIGWIG_DIR = OUTPUT_DIR / "bigwigs"
SAMPLES_PATH = OUTPUT_DIR / "samples.tsv"
USER_AGENT = "GenomeSpy dataset recipe encode-atac-grch38"
SAMPLE_FIELDS = (
    "sampleId",
    "accession",
    "biosample",
    "organ",
    "dataset",
    "assembly",
    "outputType",
    "fileSize",
    "lab",
)


@dataclass(frozen=True)
class FileLock:
    """Identity and compact metadata for one accepted ENCODE file."""

    accession: str
    biosample: str
    organ: str
    dataset: str
    size: int
    md5: str
    sha256: str
    url: str

    @property
    def filename(self) -> str:
        """Return the accepted local filename."""

        return f"{self.accession}.bigWig"

    @property
    def output_path(self) -> Path:
        """Return the accepted output path."""

        return BIGWIG_DIR / self.filename


@dataclass(frozen=True)
class LocusSummary:
    """Scientific validation summary for one BigWig locus."""

    finite_count: int
    nonfinite_count: int
    minimum: float
    maximum: float


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-directory",
        type=Path,
        help="Reuse accepted BigWigs through ignored output symlinks.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify existing outputs without reading or downloading sources.",
    )
    parser.add_argument(
        "--update-sources",
        action="store_true",
        help="Write a fresh report and candidate table for human review.",
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


def file_locks(source: dict[str, Any]) -> list[FileLock]:
    """Parse and validate the accepted file list."""

    values = source.get("files")
    if not isinstance(values, list) or not values:
        raise ValueError("The provenance source must contain accepted files.")
    template = str(source["downloadUrlTemplate"])
    locks = [
        FileLock(
            accession=str(value["accession"]),
            biosample=str(value["biosample"]),
            organ=str(value["organ"]),
            dataset=str(value["dataset"]),
            size=int(value["fileSizeBytes"]),
            md5=str(value["md5"]),
            sha256=str(value["sha256"]),
            url=template.format(accession=value["accession"]),
        )
        for value in values
    ]
    if len({lock.accession for lock in locks}) != len(locks):
        raise ValueError("Accepted ENCODE file accessions must be unique.")
    return locks


def digest(path: Path, algorithm: str) -> str:
    """Return a streaming hexadecimal digest."""

    value = hashlib.new(algorithm)
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(4 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def validate_identity(path: Path, lock: FileLock) -> None:
    """Require one file to match ENCODE and local accepted checksums."""

    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size != lock.size:
        raise ValueError(f"File size does not match provenance: {path}")
    if digest(path, "md5") != lock.md5:
        raise ValueError(f"ENCODE MD5 does not match provenance: {path}")
    if digest(path, "sha256") != lock.sha256:
        raise ValueError(f"SHA-256 does not match provenance: {path}")


def download(lock: FileLock) -> None:
    """Download one large file atomically, resuming a partial response."""

    destination = lock.output_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    offset = temporary.stat().st_size if temporary.exists() else 0
    headers = {"User-Agent": USER_AGENT}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    request = Request(lock.url, headers=headers)
    with urlopen(request) as response:
        resume = offset > 0 and response.status == 206
        mode = "ab" if resume else "wb"
        with temporary.open(mode) as output_file:
            shutil.copyfileobj(response, output_file)
    validate_identity(temporary, lock)
    temporary.replace(destination)


def link_local_source(source_path: Path, lock: FileLock) -> None:
    """Install an ignored symlink after validating a retained local source."""

    source_path = source_path.expanduser().resolve()
    validate_identity(source_path, lock)
    destination = lock.output_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".link")
    temporary.unlink(missing_ok=True)
    try:
        temporary.symlink_to(source_path)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def prepare_bigwigs(locks: list[FileLock], directory: Path | None) -> None:
    """Download missing files or link an explicit local source directory."""

    source_directory = directory.expanduser().resolve() if directory else None
    for lock in locks:
        if source_directory is not None:
            link_local_source(source_directory / lock.filename, lock)
        elif not lock.output_path.exists():
            download(lock)


def sample_table(locks: list[FileLock], source: dict[str, Any]) -> str:
    """Return deterministic compact sample metadata."""

    rows = ["\t".join(SAMPLE_FIELDS)]
    for lock in locks:
        values = (
            lock.accession,
            lock.accession,
            lock.biosample,
            lock.organ,
            f"/annotations/{lock.dataset}/",
            str(source["assembly"]),
            str(source["outputType"]),
            str(lock.size),
            str(source["lab"]),
        )
        if any("\t" in value or "\n" in value or "\r" in value for value in values):
            raise ValueError(f"Invalid TSV metadata for {lock.accession}.")
        rows.append("\t".join(values))
    return "\n".join(rows) + "\n"


def write_text_atomic(path: Path, text: str) -> None:
    """Write UTF-8 text atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    try:
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def manifest_sha256(locks: list[FileLock]) -> str:
    """Return the accepted compact file-manifest fingerprint."""

    manifest = "".join(
        f"{lock.accession}\t{lock.size}\t{lock.md5}\t{lock.sha256}\n" for lock in locks
    )
    return hashlib.sha256(manifest.encode()).hexdigest()


def validate_bigwig(path: Path, provenance: dict[str, Any]) -> LocusSummary:
    """Validate the GRCh38 header and initial-locus signal."""

    validation = provenance["validation"]
    locus = provenance["parameters"]["initialLocus"]
    expected_lengths = validation["grch38PrimaryLengths"]
    with pyBigWig.open(str(path)) as bigwig:
        if not bigwig.isBigWig():
            raise ValueError(f"Not a BigWig file: {path}")
        chromosomes: dict[str, int] = bigwig.chroms()
        if len(chromosomes) != int(validation["bigWigChromosomeCount"]):
            raise ValueError(f"Unexpected chromosome count: {path}")
        for chrom, length in expected_lengths.items():
            if chromosomes.get(chrom) != int(length):
                raise ValueError(f"Unexpected {chrom} length: {path}")
        intervals = list(
            bigwig.intervals(
                str(locus["chrom"]), int(locus["start"]), int(locus["end"])
            )
            or []
        )

    finite = [float(value) for _, _, value in intervals if math.isfinite(value)]
    nonfinite_count = len(intervals) - len(finite)
    if not finite or max(finite) <= 0:
        raise ValueError(f"No finite positive signal at the initial locus: {path}")
    if nonfinite_count == 0:
        raise ValueError(f"Expected source NaN values at the initial locus: {path}")
    return LocusSummary(
        finite_count=len(finite),
        nonfinite_count=nonfinite_count,
        minimum=min(finite),
        maximum=max(finite),
    )


def validate_range(values: list[int | float], expected: list[Any], label: str) -> None:
    """Require an observed minimum and maximum to match provenance."""

    if [min(values), max(values)] != expected:
        raise ValueError(f"{label} range does not match provenance.")


def validate_outputs(
    locks: list[FileLock], source: dict[str, Any], provenance: dict[str, Any]
) -> None:
    """Validate all accepted files, metadata, and scientific summaries."""

    outputs = provenance["outputs"]
    validation = provenance["validation"]
    if len(locks) != int(outputs["bigWigs"]["fileCount"]):
        raise ValueError("BigWig file count does not match provenance.")
    if sum(lock.size for lock in locks) != int(
        outputs["bigWigs"]["totalFileSizeBytes"]
    ):
        raise ValueError("BigWig total byte size does not match provenance.")
    if manifest_sha256(locks) != outputs["bigWigs"]["manifestSha256"]:
        raise ValueError("BigWig manifest fingerprint does not match provenance.")

    expected_samples = sample_table(locks, source)
    if SAMPLES_PATH.read_text(encoding="utf-8") != expected_samples:
        raise ValueError("samples.tsv does not match accepted metadata.")
    if digest(SAMPLES_PATH, "sha256") != outputs["samples"]["sha256"]:
        raise ValueError("samples.tsv fingerprint does not match provenance.")

    summaries: list[LocusSummary] = []
    for lock in locks:
        validate_identity(lock.output_path, lock)
        summaries.append(validate_bigwig(lock.output_path, provenance))
    validate_range(
        [summary.finite_count for summary in summaries],
        validation["initialLocusFiniteValueCountRange"],
        "Finite-value count",
    )
    validate_range(
        [summary.nonfinite_count for summary in summaries],
        validation["initialLocusNonfiniteValueCountRange"],
        "Non-finite-value count",
    )
    validate_range(
        [summary.minimum for summary in summaries],
        validation["initialLocusPerFileMinimumRange"],
        "Per-file minimum",
    )
    validate_range(
        [summary.maximum for summary in summaries],
        validation["initialLocusPerFileMaximumRange"],
        "Per-file maximum",
    )


def report_rows(text: str) -> list[dict[str, str]]:
    """Parse an ENCODE report with its explanatory preamble."""

    lines = text.splitlines()
    header_index = next(
        (index for index, line in enumerate(lines) if line.startswith("ID\t")), None
    )
    if header_index is None:
        raise ValueError("Could not find the ENCODE report header.")
    return list(
        csv.DictReader(io.StringIO("\n".join(lines[header_index:])), delimiter="\t")
    )


def selection_score(row: dict[str, str]) -> int:
    """Score a metadata row for the technical integration fixture."""

    score = 4 * bool(row.get("Organ")) + 4 * bool(row.get("Biosample name"))
    labels = f"{row.get('Biosample name', '')} {row.get('Organ', '')}".lower()
    if any(
        term in labels
        for term in ("blood", "t-cell", "natural killer", "dendritic", "cd8", "cd4")
    ):
        score += 2
    size = int(row.get("File size") or 0)
    if 0 < size < 400_000_000:
        score += 2
    return score


def update_sources(source: dict[str, Any], provenance: dict[str, Any]) -> None:
    """Write a fresh source report and deterministic candidates for review."""

    request = Request(str(source["reportUrl"]), headers={"User-Agent": USER_AGENT})
    with urlopen(request) as response:
        text = response.read().decode("utf-8")
    report_path = DOWNLOAD_DIR / "encode-atac-grch38.tsv"
    write_text_atomic(report_path, text)

    selection = provenance["parameters"]["updateSourcesSelection"]
    filters = selection["filters"]
    candidates = [
        row
        for row in report_rows(text)
        if row.get("Accession")
        and row.get("Download URL")
        and all(row.get(field) == value for field, value in filters.items())
    ]
    candidates.sort(key=lambda row: (-selection_score(row), row["Accession"]))
    candidates = candidates[: int(selection["limit"])]
    fields = (
        "accession",
        "biosample",
        "organ",
        "dataset",
        "assembly",
        "outputType",
        "fileSize",
        "lab",
        "url",
    )
    lines = ["\t".join(fields)]
    for row in candidates:
        values = (
            row["Accession"],
            row["Biosample name"],
            row["Organ"],
            row["Dataset"],
            row["Genome assembly"],
            row["Output type"],
            row["File size"],
            row["Lab"],
            "https://www.encodeproject.org" + row["Download URL"],
        )
        lines.append("\t".join(value.replace("\t", " ") for value in values))
    candidate_path = WORK_DIR / "source-candidates.tsv"
    write_text_atomic(candidate_path, "\n".join(lines) + "\n")
    print(
        f"Wrote {len(candidates)} review candidates. "
        "Accepted provenance was not changed."
    )


def main() -> None:
    """Prepare, verify, or review source candidates."""

    args = parse_args()
    if args.update_sources and (args.verify_only or args.source_directory is not None):
        raise ValueError("--update-sources cannot be combined with other modes.")
    if args.verify_only and args.source_directory is not None:
        raise ValueError("--verify-only cannot be combined with --source-directory.")

    provenance = load_provenance()
    source = source_record(provenance)
    if args.update_sources:
        update_sources(source, provenance)
        return

    locks = file_locks(source)
    if not args.verify_only:
        prepare_bigwigs(locks, args.source_directory)
        write_text_atomic(SAMPLES_PATH, sample_table(locks, source))
    validate_outputs(locks, source, provenance)
    action = "Verified" if args.verify_only else "Prepared and verified"
    print(f"{action} {len(locks)} ENCODE ATAC BigWigs and sample metadata.")


if __name__ == "__main__":
    main()
