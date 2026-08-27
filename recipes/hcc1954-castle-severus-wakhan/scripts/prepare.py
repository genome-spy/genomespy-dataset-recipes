#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0

# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""Prepare the pinned HCC1954 Severus VCF and Wakhan copy-number track."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import tarfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

RECIPE_DIR = Path(__file__).resolve().parents[1]
DOWNLOAD_DIR = RECIPE_DIR / "download"
WORK_DIR = RECIPE_DIR / "work" / "selected"
OUTPUT_DIR = RECIPE_DIR / "output"
PROVENANCE_PATH = RECIPE_DIR / "provenance.json"
USER_AGENT = "GenomeSpy dataset recipe hcc1954-castle-severus-wakhan"
WAKHAN_SOLUTION = "4.57_0.99_0.9"
WAKHAN_PLOIDY = 4.57

CHROMOSOME_LENGTHS = {
    "chr1": 248_956_422,
    "chr2": 242_193_529,
    "chr3": 198_295_559,
    "chr4": 190_214_555,
    "chr5": 181_538_259,
    "chr6": 170_805_979,
    "chr7": 159_345_973,
    "chr8": 145_138_636,
    "chr9": 138_394_717,
    "chr10": 133_797_422,
    "chr11": 135_086_622,
    "chr12": 133_275_309,
    "chr13": 114_364_328,
    "chr14": 107_043_718,
    "chr15": 101_991_189,
    "chr16": 90_338_345,
    "chr17": 83_257_441,
    "chr18": 80_373_285,
    "chr19": 58_617_616,
    "chr20": 64_444_167,
    "chr21": 46_709_983,
    "chr22": 50_818_468,
    "chrX": 156_040_895,
    "chrY": 57_227_415,
}
AUTOSOMES = tuple(f"chr{number}" for number in range(1, 23))
CHROMOSOME_ORDER = {chrom: index for index, chrom in enumerate(AUTOSOMES)}
COPY_NUMBER_FIELDS = [
    "chrom",
    "start",
    "end",
    "haplotype_1_copy_number",
    "haplotype_2_copy_number",
    "total_copy_number",
    "relative_copy_ratio",
    "haplotype_1_coverage",
    "haplotype_2_coverage",
    "confidence",
    "sv_breakpoint_ids",
]


@dataclass(frozen=True)
class MemberLock:
    """Identity and local name for one selected archive member."""

    identifier: str
    archive_path: str
    local_name: str
    file_size_bytes: int
    sha256: str


@dataclass(frozen=True)
class CopyNumberSegment:
    """One zero-based, half-open Wakhan haplotype segment."""

    start: int
    end: int
    coverage: float
    copy_number: float
    confidence: float
    breakpoint_ids: str


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive",
        type=Path,
        help="Use this pinned archive instead of the ignored download cache.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify existing outputs against provenance without preparing them.",
    )
    return parser.parse_args()


def load_provenance() -> dict[str, Any]:
    """Load the committed accepted-run record."""

    value: Any = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("provenance.json must contain an object.")
    return value


def digest(path: Path, algorithm: str = "sha256") -> str:
    """Return a hexadecimal file digest."""

    value = hashlib.new(algorithm)
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def archive_digests(path: Path) -> tuple[str, str]:
    """Return MD5 and SHA-256 in one pass over the large source archive."""

    md5 = hashlib.md5(usedforsecurity=False)
    sha256 = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(4 * 1024 * 1024), b""):
            md5.update(chunk)
            sha256.update(chunk)
    return md5.hexdigest(), sha256.hexdigest()


def source_record(provenance: dict[str, Any]) -> dict[str, Any]:
    """Return the single pinned source record."""

    sources = provenance.get("sources")
    if not isinstance(sources, list) or len(sources) != 1:
        raise ValueError("provenance.json must contain exactly one source.")
    source = sources[0]
    if not isinstance(source, dict):
        raise ValueError("The provenance source must be an object.")
    return source


def member_locks(source: dict[str, Any]) -> dict[str, MemberLock]:
    """Return selected archive members keyed by their identifiers."""

    members = source.get("members")
    if not isinstance(members, list) or not members:
        raise ValueError("The provenance source must contain selected members.")
    locks: dict[str, MemberLock] = {}
    for value in members:
        if not isinstance(value, dict):
            raise ValueError("Archive member locks must be objects.")
        lock = MemberLock(
            identifier=str(value["id"]),
            archive_path=str(value["path"]),
            local_name=str(value["localName"]),
            file_size_bytes=int(value["fileSizeBytes"]),
            sha256=str(value["sha256"]),
        )
        if lock.identifier in locks:
            raise ValueError(f"Duplicate archive member id: {lock.identifier}")
        locks[lock.identifier] = lock
    return locks


def validate_file(path: Path, expected_size: int, expected_sha256: str) -> None:
    """Require exact size and SHA-256 identity."""

    if not path.is_file():
        raise FileNotFoundError(f"Required file is missing: {path}")
    if path.stat().st_size != expected_size:
        raise ValueError(f"File size does not match provenance: {path}")
    if digest(path) != expected_sha256:
        raise ValueError(f"SHA-256 does not match provenance: {path}")


def validate_archive(path: Path, source: dict[str, Any]) -> None:
    """Require the exact accepted Zenodo archive."""

    if not path.is_file():
        raise FileNotFoundError(f"Pinned source archive is missing: {path}")
    if path.stat().st_size != int(source["fileSizeBytes"]):
        raise ValueError("Source archive size does not match provenance.")
    md5, sha256 = archive_digests(path)
    if md5 != source["md5"] or sha256 != source["sha256"]:
        raise ValueError("Source archive checksums do not match provenance.")


def download_archive(destination: Path, source: dict[str, Any]) -> None:
    """Download the pinned Zenodo archive atomically."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    request = Request(str(source["url"]), headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request) as response, temporary.open("wb") as output_file:
            shutil.copyfileobj(response, output_file)
        validate_archive(temporary, source)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def resolve_archive(explicit: Path | None, source: dict[str, Any]) -> Path:
    """Return and validate an explicit or cached source archive."""

    if explicit is None:
        archive = DOWNLOAD_DIR / str(source["filename"])
        if not archive.exists():
            download_archive(archive, source)
            return archive
    else:
        archive = explicit.expanduser().resolve()
    validate_archive(archive, source)
    return archive


def cached_members(locks: dict[str, MemberLock]) -> dict[str, Path] | None:
    """Return validated cached members, or None if extraction is needed."""

    paths = {
        identifier: WORK_DIR / lock.local_name for identifier, lock in locks.items()
    }
    try:
        for identifier, path in paths.items():
            lock = locks[identifier]
            validate_file(path, lock.file_size_bytes, lock.sha256)
    except (FileNotFoundError, ValueError):
        return None
    return paths


def extract_members(archive: Path, locks: dict[str, MemberLock]) -> dict[str, Path]:
    """Extract and verify only the selected archive members."""

    cached = cached_members(locks)
    if cached is not None:
        return cached

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    by_archive_path = {lock.archive_path: lock for lock in locks.values()}
    remaining = set(by_archive_path)
    with tarfile.open(archive, mode="r|gz") as input_archive:
        for entry in input_archive:
            lock = by_archive_path.get(entry.name)
            if lock is None:
                continue
            input_file = input_archive.extractfile(entry)
            if input_file is None:
                raise ValueError(f"Archive member is not a regular file: {entry.name}")
            destination = WORK_DIR / lock.local_name
            temporary = destination.with_name(destination.name + ".part")
            try:
                with input_file, temporary.open("wb") as output_file:
                    shutil.copyfileobj(input_file, output_file)
                validate_file(temporary, lock.file_size_bytes, lock.sha256)
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)
            remaining.remove(entry.name)
            if not remaining:
                break
    if remaining:
        raise ValueError("Missing selected archive members: " + ", ".join(remaining))
    paths = cached_members(locks)
    if paths is None:
        raise ValueError("Extracted member validation failed.")
    return paths


def validate_source_linkage(paths: dict[str, Path]) -> None:
    """Require the selected rank and exact SV-to-copy-number linkage evidence."""

    with paths["solutionRanks"].open(encoding="utf-8", newline="") as input_file:
        rows = list(csv.DictReader(input_file, delimiter="\t"))
    if not rows or rows[0] != {
        "repository_name": WAKHAN_SOLUTION,
        "dna_purity": "1.0",
        "cell_purity": "0.99",
        "ploidy": "4.57",
        "confidence": "0.9",
        "solution_rank": "1",
    }:
        raise ValueError("The accepted Wakhan solution is not rank 1.")

    log = paths["wakhanLog"].read_text(encoding="utf-8")
    required = (
        "--breakpoints severus/somatic_SVs/severus_somatic.vcf",
        "cellular fraction 0.99, ploidy 4.57 and tumor dna fraction 1.0",
        "solution_1 ->",
        "/4.57_0.99_0.9",
    )
    if not all(value in log for value in required):
        raise ValueError("Wakhan log does not establish the accepted source linkage.")


def read_copy_number_segments(path: Path) -> dict[str, list[CopyNumberSegment]]:
    """Read and convert one Wakhan haplotype segmentation."""

    segments: dict[str, list[CopyNumberSegment]] = {}
    with path.open(encoding="utf-8", newline="") as input_file:
        reader = csv.DictReader(
            (
                line.removeprefix("#")
                for line in input_file
                if not line.startswith("#") or line.startswith("#chr\t")
            ),
            delimiter="\t",
        )
        for row in reader:
            chrom = row["chr"]
            if chrom not in CHROMOSOME_ORDER:
                continue
            segment = CopyNumberSegment(
                start=max(0, int(row["start"]) - 1),
                end=int(row["end"]),
                coverage=float(row["coverage"]),
                copy_number=float(row["copynumber_state"]),
                confidence=float(row["confidence"]),
                breakpoint_ids=row["svs_breakpoints_ids"],
            )
            if not (
                0 <= segment.start < segment.end <= CHROMOSOME_LENGTHS[chrom]
                and math.isfinite(segment.coverage)
                and math.isfinite(segment.copy_number)
                and math.isfinite(segment.confidence)
                and segment.coverage >= 0
                and segment.copy_number >= 0
                and 0 <= segment.confidence <= 1
            ):
                raise ValueError(f"Invalid Wakhan segment on {chrom}.")
            segments.setdefault(chrom, []).append(segment)

    if set(segments) != set(AUTOSOMES):
        raise ValueError("Wakhan copy numbers must cover chr1 through chr22.")
    for chrom, chrom_segments in segments.items():
        if chrom_segments[0].start != 0:
            raise ValueError(f"Wakhan segments do not begin at zero on {chrom}.")
        if any(
            right.start != left.end
            for left, right in zip(chrom_segments, chrom_segments[1:], strict=False)
        ):
            raise ValueError(f"Wakhan segments are not contiguous on {chrom}.")
    return segments


def join_breakpoint_ids(first: str, second: str) -> str:
    """Preserve distinct source annotation strings in haplotype order."""

    return "; ".join(dict.fromkeys((first + "; " + second).split("; ")))


def write_copy_numbers(hp1: Path, hp2: Path, destination: Path) -> int:
    """Synchronize haplotype segments and write the accepted copy-number table."""

    first_by_chrom = read_copy_number_segments(hp1)
    second_by_chrom = read_copy_number_segments(hp2)
    rows: list[dict[str, object]] = []
    for chrom in AUTOSOMES:
        first_segments = first_by_chrom[chrom]
        second_segments = second_by_chrom[chrom]
        first_index = 0
        second_index = 0
        while first_index < len(first_segments) and second_index < len(second_segments):
            first = first_segments[first_index]
            second = second_segments[second_index]
            start = max(first.start, second.start)
            end = min(first.end, second.end)
            if start < end:
                total = first.copy_number + second.copy_number
                rows.append(
                    {
                        "chrom": chrom,
                        "start": start,
                        "end": end,
                        "haplotype_1_copy_number": first.copy_number,
                        "haplotype_2_copy_number": second.copy_number,
                        "total_copy_number": total,
                        "relative_copy_ratio": format(total / WAKHAN_PLOIDY, ".3g"),
                        "haplotype_1_coverage": first.coverage,
                        "haplotype_2_coverage": second.coverage,
                        "confidence": min(first.confidence, second.confidence),
                        "sv_breakpoint_ids": join_breakpoint_ids(
                            first.breakpoint_ids, second.breakpoint_ids
                        ),
                    }
                )
            if first.end <= second.end:
                first_index += 1
            if second.end <= first.end:
                second_index += 1

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    try:
        with temporary.open("w", encoding="utf-8", newline="") as output_file:
            writer = csv.DictWriter(
                output_file, fieldnames=COPY_NUMBER_FIELDS, delimiter="\t"
            )
            writer.writeheader()
            writer.writerows(rows)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return len(rows)


def copy_structural_variants(source: Path, destination: Path) -> None:
    """Copy the pinned VCF without changing its bytes."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    try:
        shutil.copyfile(source, temporary)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def parse_info(value: str) -> dict[str, str]:
    """Parse one VCF INFO column."""

    return {item.partition("=")[0]: item.partition("=")[2] for item in value.split(";")}


def validate_structural_variants(path: Path, expected: dict[str, Any]) -> int:
    """Validate gzip, GRCh38 headers, calls, filters, and BND mate pairing."""

    metadata: dict[str, str] = {}
    contigs: dict[str, int] = {}
    filters: Counter[str] = Counter()
    sv_types: Counter[str] = Counter()
    record_ids: set[str] = set()
    bnd_mates: list[str] = []
    sample = ""
    with path.open("r", encoding="utf-8", newline="") as input_file:
        for line in input_file:
            if line.startswith("##"):
                key, separator, value = line[2:].rstrip().partition("=")
                if separator and key in {"fileformat", "source", "fileDate"}:
                    metadata[key] = value
                if line.startswith("##contig=<ID="):
                    contig_fields = dict(
                        item.split("=", maxsplit=1)
                        for item in line.rstrip()[10:-1].split(",")
                    )
                    contigs[contig_fields["ID"]] = int(contig_fields["length"])
                continue
            columns = line.rstrip("\r\n").split("\t")
            if columns[0] == "#CHROM":
                if len(columns) != 10:
                    raise ValueError("Expected exactly one VCF sample.")
                sample = columns[9]
                continue
            if len(columns) != 10:
                raise ValueError("Unexpected VCF record width.")
            chrom, pos_text, record_id = columns[0], columns[1], columns[2]
            if chrom not in CHROMOSOME_LENGTHS:
                raise ValueError(f"Unexpected VCF contig: {chrom}")
            if not 1 <= int(pos_text) <= CHROMOSOME_LENGTHS[chrom]:
                raise ValueError(f"VCF position outside {chrom}.")
            if record_id in record_ids:
                raise ValueError(f"Duplicate VCF record ID: {record_id}")
            record_ids.add(record_id)
            filters[columns[6]] += 1
            info = parse_info(columns[7])
            sv_type = info["SVTYPE"]
            sv_types[sv_type] += 1
            if sv_type == "BND":
                bnd_mates.append(info["MATE_ID"])

    if contigs != CHROMOSOME_LENGTHS:
        raise ValueError("VCF contig headers do not match GRCh38 primary contigs.")
    observed = {
        "fileFormat": metadata.get("fileformat"),
        "caller": metadata.get("source"),
        "fileDate": metadata.get("fileDate"),
        "sample": sample,
        "filters": dict(sorted(filters.items())),
        "svTypeCounts": dict(sorted(sv_types.items())),
        "bndMatePairs": len(bnd_mates) // 2,
        "allBndMatesPresent": all(mate in record_ids for mate in bnd_mates),
    }
    for observed_key, observed_value in observed.items():
        if observed_value != expected[observed_key]:
            raise ValueError(
                f"VCF validation mismatch for {observed_key}: {observed_value}"
            )
    return len(record_ids)


def validate_copy_numbers(path: Path, expected: dict[str, Any]) -> int:
    """Validate the accepted copy-number table's schema and scientific ranges."""

    with path.open(encoding="utf-8", newline="") as input_file:
        reader = csv.DictReader(input_file, delimiter="\t")
        if reader.fieldnames != COPY_NUMBER_FIELDS:
            raise ValueError("Unexpected copy-number output fields.")
        rows = list(reader)
    if not rows:
        raise ValueError("Copy-number output is empty.")

    keys: list[tuple[int, int, int]] = []
    total_copy_numbers: list[float] = []
    relative_ratios: list[float] = []
    confidences: list[float] = []
    for row in rows:
        chrom = row["chrom"]
        if chrom not in CHROMOSOME_ORDER:
            raise ValueError(f"Unexpected copy-number contig: {chrom}")
        start = int(row["start"])
        end = int(row["end"])
        if not 0 <= start < end <= CHROMOSOME_LENGTHS[chrom]:
            raise ValueError(f"Invalid copy-number interval on {chrom}.")
        keys.append((CHROMOSOME_ORDER[chrom], start, end))
        total_copy_numbers.append(float(row["total_copy_number"]))
        relative_ratios.append(float(row["relative_copy_ratio"]))
        confidences.append(float(row["confidence"]))

    observed = {
        "chromosomes": len({row["chrom"] for row in rows}),
        "sorted": keys == sorted(keys),
        "positiveIntervals": all(start < end for _chrom, start, end in keys),
        "totalCopyNumberRange": [min(total_copy_numbers), max(total_copy_numbers)],
        "relativeCopyRatioRange": [min(relative_ratios), max(relative_ratios)],
        "confidenceRange": [min(confidences), max(confidences)],
        "chr21Segments": sum(row["chrom"] == "chr21" for row in rows),
        "chr22Segments": sum(row["chrom"] == "chr22" for row in rows),
    }
    for key, value in observed.items():
        if value != expected[key]:
            raise ValueError(f"Copy-number validation mismatch for {key}: {value}")
    return len(rows)


def verify_fingerprint(path: Path, expected: dict[str, Any]) -> None:
    """Compare one output with its accepted size and checksum."""

    validate_file(path, int(expected["fileSizeBytes"]), str(expected["sha256"]))


def verify_outputs(provenance: dict[str, Any]) -> None:
    """Validate accepted outputs and their committed fingerprints."""

    outputs = provenance["outputs"]
    validation = provenance["validation"]
    structural_variants = OUTPUT_DIR / "severus-somatic.vcf"
    copy_numbers = OUTPUT_DIR / "copy-numbers.tsv"
    verify_fingerprint(structural_variants, outputs["structuralVariants"])
    verify_fingerprint(copy_numbers, outputs["copyNumbers"])
    sv_records = validate_structural_variants(
        structural_variants, validation["structuralVariants"]
    )
    cn_records = validate_copy_numbers(copy_numbers, validation["copyNumbers"])
    if sv_records != outputs["structuralVariants"]["recordCount"]:
        raise ValueError("Structural-variant record count does not match provenance.")
    if cn_records != outputs["copyNumbers"]["recordCount"]:
        raise ValueError("Copy-number record count does not match provenance.")
    print(f"Verified {sv_records} SV records and {cn_records} copy-number rows.")


def prepare(explicit_archive: Path | None, provenance: dict[str, Any]) -> None:
    """Extract the pinned sources and create both accepted outputs."""

    source = source_record(provenance)
    locks = member_locks(source)
    archive = resolve_archive(explicit_archive, source)
    paths = extract_members(archive, locks)
    validate_source_linkage(paths)
    copy_structural_variants(
        paths["structuralVariants"], OUTPUT_DIR / "severus-somatic.vcf"
    )
    write_copy_numbers(
        paths["haplotype1CopyNumbers"],
        paths["haplotype2CopyNumbers"],
        OUTPUT_DIR / "copy-numbers.tsv",
    )
    verify_outputs(provenance)


def main() -> None:
    """Prepare or verify the HCC1954 recipe outputs."""

    arguments = parse_args()
    provenance = load_provenance()
    if arguments.verify_only:
        verify_outputs(provenance)
    else:
        prepare(arguments.archive, provenance)


if __name__ == "__main__":
    main()
