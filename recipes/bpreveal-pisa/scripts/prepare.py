#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0

# mypy: ignore_missing_imports=True
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "h5py==3.15.1",
#   "numpy==2.4.6",
#   "pyarrow==24.0.0",
#   "pyBigWig==0.3.24",
#   "pytest==8.4.2",
# ]
# ///

"""Download, selectively extract, and wrangle the BPReveal PISA figure data."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import math
import tarfile
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import h5py  # type: ignore[import-not-found]
import numpy as np  # type: ignore[import-not-found]
import pyarrow as pa  # type: ignore[import-not-found]
import pyarrow.parquet as pq  # type: ignore[import-not-found]
import pyBigWig  # type: ignore[import-not-found]

RECIPE_DIR = Path(__file__).resolve().parents[1]
DOWNLOAD_DIR = RECIPE_DIR / "download"
WORK_DIR = RECIPE_DIR / "work"
SELECTED_DIR = WORK_DIR / "selected"
OUTPUT_DIR = RECIPE_DIR / "output"
PROVENANCE_PATH = RECIPE_DIR / "provenance.json"
EXTRACTION_MANIFEST = WORK_DIR / "extracted-members.json"
RUN_MANIFEST = WORK_DIR / "run-manifest.json"
ARCHIVE_INDEX = WORK_DIR / "archive-members.txt"
USER_AGENT = "GenomeSpy dataset recipe bpreveal-pisa"
LOG2_E = math.log2(math.e)
DOWNLOAD_REPORT_BYTES = 1024**3
DOWNLOAD_SOCKET_TIMEOUT_SECONDS = 60
DOWNLOAD_MAX_CONSECUTIVE_FAILURES = 100
DOWNLOAD_MAX_RETRY_DELAY_SECONDS = 30

LINK_SCHEMA = pa.schema(
    [
        pa.field("source", pa.int32(), nullable=False),
        pa.field("target", pa.int32(), nullable=False),
        pa.field("effect", pa.float32(), nullable=False),
    ]
)
MATRIX_SCHEMA = pa.schema(
    [
        pa.field("input", pa.int32(), nullable=False),
        pa.field("output", pa.int32(), nullable=False),
        pa.field("effect", pa.float32(), nullable=False),
    ]
)
TRACK_SCHEMA = pa.schema(
    [
        pa.field("position", pa.int32(), nullable=False),
        pa.field("track", pa.string(), nullable=False),
        pa.field("value", pa.float32(), nullable=False),
        pa.field("base", pa.string(), nullable=False),
    ]
)
MOTIF_SCHEMA = pa.schema(
    [
        pa.field("chrom", pa.string(), nullable=False),
        pa.field("start", pa.int32(), nullable=False),
        pa.field("end", pa.int32(), nullable=False),
        pa.field("name", pa.string(), nullable=False),
        pa.field("score", pa.string(), nullable=False),
        pa.field("strand", pa.string(), nullable=False),
    ]
)


@dataclass(frozen=True)
class MemberSpec:
    """One archive member selected by a unique path suffix."""

    identifier: str
    suffix: str
    local_name: str


@dataclass(frozen=True)
class TrackSpec:
    """One BigWig track exported for a locus."""

    member: str
    label: str
    multiplier: float = 1.0
    region: str = "input"


@dataclass(frozen=True)
class Panel:
    """Coordinates and source members for one figure panel."""

    identifier: str
    assembly: str
    chrom: str
    genome_window_start: int
    midpoint_offset: int
    input_width: int
    output_width: int
    pisa_members: tuple[str, ...]
    tracks: tuple[TrackSpec, ...]
    motifs_member: str
    sequence_member: str
    sequence_padding: int
    threshold: float | None
    color_span: float

    @property
    def input_start_offset(self) -> int:
        return self.midpoint_offset - self.input_width // 2

    @property
    def input_end_offset(self) -> int:
        return self.input_start_offset + self.input_width

    @property
    def output_start_offset(self) -> int:
        return self.midpoint_offset - self.output_width // 2

    @property
    def output_end_offset(self) -> int:
        return self.output_start_offset + self.output_width

    @property
    def genomic_input_start(self) -> int:
        return self.genome_window_start + self.input_start_offset

    @property
    def genomic_input_end(self) -> int:
        return self.genome_window_start + self.input_end_offset

    @property
    def genomic_output_start(self) -> int:
        return self.genome_window_start + self.output_start_offset

    @property
    def genomic_output_end(self) -> int:
        return self.genome_window_start + self.output_end_offset


MEMBERS = (
    MemberSpec(
        "fig2cdPisa",
        "tmp/atac/shap/pisa_residual.h5",
        "fig2cd-atac-pisa.h5",
    ),
    MemberSpec(
        "fig2cdPrediction",
        "tmp/atac/pred/residual.bw",
        "fig2cd-atac-prediction.bw",
    ),
    MemberSpec(
        "fig2cdImportance",
        "tmp/atac/shap/counts_residual.bw",
        "fig2cd-atac-importance.bw",
    ),
    MemberSpec(
        "fig2cdMotifs",
        "tmp/atac/scan/counts_residual_filtered.bed",
        "fig2cd-atac-motifs.bed",
    ),
    MemberSpec(
        "fig2cdSequence",
        "tmp/atac/shap/pisa_regions.fa",
        "fig2cd-atac-pisa-regions.fa",
    ),
)

PANELS = (
    Panel(
        identifier="fig2cd-atac",
        assembly="dm6",
        chrom="chrX",
        genome_window_start=15_643_659,
        midpoint_offset=3290,
        input_width=601,
        output_width=901,
        pisa_members=("fig2cdPisa",),
        tracks=(
            TrackSpec("fig2cdPrediction", "prediction", region="output"),
            TrackSpec("fig2cdImportance", "importance"),
        ),
        motifs_member="fig2cdMotifs",
        sequence_member="fig2cdSequence",
        sequence_padding=557,
        threshold=0.03,
        color_span=0.15,
    ),
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage",
        choices=("all", "download", "index", "extract", "wrangle", "verify"),
        default="all",
        help="Run the full workflow or one restartable stage.",
    )
    parser.add_argument(
        "--archive",
        type=Path,
        help=(
            "Use an existing archive rather than "
            "download/zenodo-bpreveal-files.tar.bz2."
        ),
    )
    parser.add_argument(
        "--panel",
        choices=("all", *(panel.identifier for panel in PANELS)),
        default="all",
        help="Prepare all configured panels or one panel and its required inputs.",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run focused synthetic tests instead of processing the real archive.",
    )
    return parser.parse_args()


def load_provenance() -> dict[str, Any]:
    """Load the committed source and output contract."""

    value: Any = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("provenance.json must contain an object")
    return value


def source_record() -> dict[str, Any]:
    """Return the single pinned source record."""

    sources = load_provenance().get("sources")
    if not isinstance(sources, list) or len(sources) != 1:
        raise ValueError("provenance.json must contain exactly one source")
    source = sources[0]
    if not isinstance(source, dict):
        raise ValueError("source record must be an object")
    return source


def file_digest(path: Path, algorithm: str = "sha256") -> str:
    """Return a hexadecimal digest without loading the file into memory."""

    digest = hashlib.new(algorithm, usedforsecurity=False)
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_archive(path: Path, source: dict[str, Any]) -> None:
    """Require the exact Zenodo archive recorded in provenance."""

    if not path.is_file():
        raise FileNotFoundError(path)
    expected_size = int(source["fileSizeBytes"])
    actual_size = path.stat().st_size
    if actual_size != expected_size:
        raise ValueError(
            f"Archive size mismatch: {actual_size} bytes != {expected_size} bytes"
        )
    actual_md5 = file_digest(path, "md5")
    if actual_md5 != source["md5"]:
        raise ValueError(f"Archive MD5 mismatch: {actual_md5} != {source['md5']}")


def download_archive(destination: Path, source: dict[str, Any]) -> Path:
    """Download the pinned archive with resumption and stalled-socket recovery."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        verify_archive(destination, source)
        print(f"Using verified archive: {destination}")
        return destination

    temporary = destination.with_name(destination.name + ".part")
    expected_size = int(source["fileSizeBytes"])
    consecutive_failures = 0
    announced_start = False
    while True:
        existing = temporary.stat().st_size if temporary.exists() else 0
        if existing > expected_size:
            raise ValueError(f"Partial download is larger than expected: {temporary}")
        if existing == expected_size:
            break

        if not announced_start:
            action = "Resuming" if existing else "Downloading"
            print(f"{action} at {existing:,} of {expected_size:,} bytes")
            announced_start = True

        headers = {"User-Agent": USER_AGENT}
        if existing:
            headers["Range"] = f"bytes={existing}-"
        request = Request(str(source["url"]), headers=headers)
        bytes_before_attempt = existing
        try:
            response = urlopen(
                request,
                timeout=DOWNLOAD_SOCKET_TIMEOUT_SECONDS,
            )
            status = getattr(response, "status", response.getcode())
            append = existing > 0 and status == 206
            if existing and not append:
                print(
                    "Server did not honor the range request; "
                    "restarting the partial file"
                )
                existing = 0
            mode = "ab" if append else "wb"
            downloaded = existing
            next_report = (
                (downloaded // DOWNLOAD_REPORT_BYTES) + 1
            ) * DOWNLOAD_REPORT_BYTES
            with response, temporary.open(mode) as output_file:
                while chunk := response.read(8 * 1024 * 1024):
                    output_file.write(chunk)
                    downloaded += len(chunk)
                    if downloaded > expected_size:
                        raise ValueError(
                            "Server returned more bytes than the pinned archive size"
                        )
                    if downloaded >= next_report:
                        print(f"Downloaded {downloaded:,} of {expected_size:,} bytes")
                        next_report += DOWNLOAD_REPORT_BYTES
        except HTTPError as error:
            if existing and error.code == 416:
                verify_archive(temporary, source)
                temporary.replace(destination)
                return destination
            if error.code < 500 and error.code not in {408, 429}:
                raise
            download_error: BaseException = error
        except (
            TimeoutError,
            URLError,
            http.client.IncompleteRead,
            OSError,
        ) as error:
            download_error = error
        else:
            current_size = temporary.stat().st_size
            if current_size == expected_size:
                break
            download_error = RuntimeError(
                f"connection ended at {current_size:,} of {expected_size:,} bytes"
            )

        current_size = temporary.stat().st_size if temporary.exists() else 0
        if current_size > bytes_before_attempt:
            consecutive_failures = 0
        else:
            consecutive_failures += 1
        if consecutive_failures >= DOWNLOAD_MAX_CONSECUTIVE_FAILURES:
            raise RuntimeError(
                "Download made no progress after "
                f"{consecutive_failures} consecutive attempts"
            ) from download_error
        delay = min(2 ** min(consecutive_failures, 5), DOWNLOAD_MAX_RETRY_DELAY_SECONDS)
        print(
            f"Download interrupted ({download_error}); retrying from "
            f"{current_size:,} bytes in {delay} seconds"
        )
        time.sleep(delay)

    verify_archive(temporary, source)
    temporary.replace(destination)
    print(f"Verified archive: {destination}")
    return destination


def resolve_archive(explicit: Path | None, allow_download: bool) -> Path:
    """Resolve and verify an explicit or recipe-cached archive."""

    source = source_record()
    if explicit is not None:
        archive = explicit.expanduser().resolve()
        verify_archive(archive, source)
        return archive
    archive = DOWNLOAD_DIR / str(source["filename"])
    if allow_download:
        return download_archive(archive, source)
    verify_archive(archive, source)
    return archive


def copy_member(input_file: IO[bytes], destination: Path) -> dict[str, Any]:
    """Copy one member atomically and return its identity."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    sha256 = hashlib.sha256()
    size = 0
    try:
        with temporary.open("wb") as output_file:
            while chunk := input_file.read(8 * 1024 * 1024):
                output_file.write(chunk)
                sha256.update(chunk)
                size += len(chunk)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return {"fileSizeBytes": size, "sha256": sha256.hexdigest()}


def write_archive_index(archive: Path, destination: Path, archive_md5: str) -> int:
    """Write a reusable, source-identified list of every archive member."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    header = f"# archiveMd5={archive_md5}"
    if destination.is_file():
        with destination.open(encoding="utf-8") as input_file:
            if input_file.readline().rstrip("\n") == header:
                count = sum(1 for _ in input_file)
                print(f"Using archive member index with {count:,} entries")
                return count

    temporary = destination.with_name(destination.name + ".part")
    temporary.unlink(missing_ok=True)
    count = 0
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as output_file:
            output_file.write(header + "\n")
            with tarfile.open(archive, mode="r:bz2") as input_archive:
                for entry in input_archive:
                    output_file.write(entry.name + "\n")
                    count += 1
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Indexed {count:,} archive members: {destination}")
    return count


def selected_paths(members: Sequence[MemberSpec] = MEMBERS) -> dict[str, Path]:
    """Return selected local member paths keyed by stable identifier."""

    return {member.identifier: SELECTED_DIR / member.local_name for member in members}


def members_for_panels(panels: Sequence[Panel]) -> tuple[MemberSpec, ...]:
    """Return archive members required by the selected panels."""

    identifiers = {
        identifier
        for panel in panels
        for identifier in (
            *panel.pisa_members,
            *(track.member for track in panel.tracks),
            panel.motifs_member,
            panel.sequence_member,
        )
    }
    return tuple(member for member in MEMBERS if member.identifier in identifiers)


def load_extraction_manifest() -> dict[str, Any] | None:
    """Load the local extraction manifest when present."""

    if not EXTRACTION_MANIFEST.is_file():
        return None
    value: Any = json.loads(EXTRACTION_MANIFEST.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else None


def validate_selected_cache(
    members: Sequence[MemberSpec] = MEMBERS,
) -> dict[str, Path] | None:
    """Return validated selected members, or None when extraction is required."""

    manifest = load_extraction_manifest()
    if manifest is None or manifest.get("archiveMd5") != source_record()["md5"]:
        return None
    identities = manifest.get("members")
    required = {member.identifier for member in members}
    if not isinstance(identities, dict) or not required.issubset(identities):
        return None
    paths = selected_paths(members)
    for identifier, path in paths.items():
        identity = identities.get(identifier)
        if not isinstance(identity, dict) or not path.is_file():
            return None
        if path.stat().st_size != identity.get("fileSizeBytes"):
            return None
        if file_digest(path) != identity.get("sha256"):
            return None
    return paths


def member_for_archive_path(name: str) -> MemberSpec | None:
    """Match an archive path against the selected suffixes."""

    normalized = name.removeprefix("./")
    matches = [
        member
        for member in MEMBERS
        if normalized == member.suffix or normalized.endswith("/" + member.suffix)
    ]
    if len(matches) > 1:
        raise ValueError(f"Ambiguous selected archive path: {name}")
    return matches[0] if matches else None


def extract_selected_members(
    archive: Path, members: Sequence[MemberSpec] = MEMBERS
) -> dict[str, Path]:
    """Scan the compressed tar once and extract only selected members."""

    cached = validate_selected_cache(members)
    if cached is not None:
        print("Using verified selected-member cache")
        return cached

    SELECTED_DIR.mkdir(parents=True, exist_ok=True)
    existing_manifest = load_extraction_manifest()
    existing_identities = (
        existing_manifest.get("members", {})
        if isinstance(existing_manifest, dict)
        and existing_manifest.get("archiveMd5") == source_record()["md5"]
        else {}
    )
    identities: dict[str, dict[str, Any]] = (
        dict(existing_identities) if isinstance(existing_identities, dict) else {}
    )
    paths = selected_paths(members)
    remaining: set[str] = set()
    for requested_member in members:
        identity = identities.get(requested_member.identifier)
        path = paths[requested_member.identifier]
        if (
            not isinstance(identity, dict)
            or not path.is_file()
            or path.stat().st_size != identity.get("fileSizeBytes")
            or file_digest(path) != identity.get("sha256")
        ):
            remaining.add(requested_member.identifier)
    if not remaining:
        raise ValueError("Selected-member cache validation failed unexpectedly")
    requested = set(remaining)
    print(f"Scanning archive for {len(remaining)} selected members")
    # BZ2File, used by seekable mode, handles concatenated bzip2 streams. The
    # streaming tar wrapper stops at the first stream in pbzip2-style archives.
    with tarfile.open(archive, mode="r:bz2") as input_archive:
        for entry in input_archive:
            member = member_for_archive_path(entry.name)
            if member is None or member.identifier not in requested:
                continue
            if member.identifier not in remaining:
                raise ValueError(f"Duplicate selected member: {entry.name}")
            if not entry.isfile():
                raise ValueError(f"Selected member is not a regular file: {entry.name}")
            input_file = input_archive.extractfile(entry)
            if input_file is None:
                raise ValueError(f"Cannot read selected member: {entry.name}")
            print(f"Extracting {entry.name}")
            with input_file:
                identity = copy_member(input_file, paths[member.identifier])
            identity["archivePath"] = entry.name
            identity["localName"] = member.local_name
            identities[member.identifier] = identity
            remaining.remove(member.identifier)
            if not remaining:
                break

    if remaining:
        missing = ", ".join(sorted(remaining))
        raise ValueError(f"Selected members not found in archive: {missing}")
    write_json_atomic(
        EXTRACTION_MANIFEST,
        {"archiveMd5": source_record()["md5"], "members": identities},
    )
    validated = validate_selected_cache(members)
    if validated is None:
        raise ValueError("Selected-member cache failed post-extraction validation")
    return validated


def require_selected_members(
    members: Sequence[MemberSpec] = MEMBERS,
) -> dict[str, Path]:
    """Require a complete, validated extraction cache."""

    paths = validate_selected_cache(members)
    if paths is None:
        raise FileNotFoundError(
            "Selected members are absent or invalid; run --stage extract first"
        )
    return paths


def read_sheared_slice(
    h5_path: Path,
    row_start: int,
    row_end: int,
    column_start: int,
    column_end: int,
) -> np.ndarray:
    """Read a BPReveal PISA slice using its sum, shear, and crop semantics."""

    if not (0 <= row_start < row_end and 0 <= column_start < column_end):
        raise ValueError("PISA slice coordinates must be non-negative and non-empty")
    output = np.zeros(
        (row_end - row_start, column_end - column_start), dtype=np.float32
    )
    with h5py.File(h5_path, "r") as input_h5:
        if "shap" not in input_h5:
            raise ValueError(f"Missing shap dataset: {h5_path}")
        shap = input_h5["shap"]
        if shap.ndim != 3 or shap.shape[2] != 4:
            raise ValueError(f"Unexpected shap dimensions in {h5_path}: {shap.shape}")
        num_rows, receptive_field, _ = shap.shape
        if row_end > num_rows or column_end > num_rows:
            raise ValueError(
                f"Requested slice exceeds sheared {num_rows}x{num_rows} matrix: "
                f"rows {row_start}:{row_end}, columns {column_start}:{column_end}"
            )
        crop_left = receptive_field // 2
        for output_row, source_row in enumerate(range(row_start, row_end)):
            first_input_index = column_start + crop_left - source_row
            last_input_index = column_end + crop_left - source_row
            valid_first = max(first_input_index, 0)
            valid_last = min(last_input_index, receptive_field)
            if valid_first >= valid_last:
                continue
            destination_first = valid_first - first_input_index
            destination_last = destination_first + valid_last - valid_first
            values = np.asarray(
                shap[source_row, valid_first:valid_last, :], dtype=np.float32
            ).sum(axis=1, dtype=np.float32)
            output[output_row, destination_first:destination_last] = values
    return output


def read_combined_slice(
    paths: dict[str, Path],
    members: Sequence[str],
    row_start: int,
    row_end: int,
    column_start: int,
    column_end: int,
) -> np.ndarray:
    """Read and sum corresponding sheared slices from one or more PISA files."""

    combined: np.ndarray | None = None
    for member in members:
        values = read_sheared_slice(
            paths[member], row_start, row_end, column_start, column_end
        )
        combined = values if combined is None else combined + values
    if combined is None:
        raise ValueError("At least one PISA member is required")
    if not np.isfinite(combined).all():
        raise ValueError("PISA slice contains non-finite values")
    return combined


def parquet_writer(path: Path, schema: pa.Schema) -> tuple[pq.ParquetWriter, Path]:
    """Create an atomic Snappy Parquet writer and its temporary path."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.unlink(missing_ok=True)
    writer = pq.ParquetWriter(
        temporary,
        schema,
        compression="snappy",
        version="2.6",
        write_statistics=True,
    )
    return writer, temporary


def finish_parquet(writer: pq.ParquetWriter, temporary: Path, path: Path) -> None:
    """Close and atomically install a Parquet file."""

    try:
        writer.close()
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def write_table_atomic(path: Path, table: pa.Table) -> int:
    """Write one small table atomically with the table's explicit schema."""

    writer, temporary = parquet_writer(path, table.schema)
    try:
        writer.write_table(table)
        finish_parquet(writer, temporary, path)
    except Exception:
        try:
            writer.close()
        finally:
            temporary.unlink(missing_ok=True)
        raise
    return table.num_rows


def write_links(path: Path, panel: Panel, values: np.ndarray) -> int:
    """Write thresholded squid links in increasing magnitude draw order."""

    if panel.threshold is None:
        raise ValueError(f"No link threshold configured for {panel.identifier}")
    mask = np.abs(values) >= panel.threshold
    rows, columns = np.nonzero(mask)
    effects = np.asarray(values[rows, columns] * LOG2_E, dtype=np.float32)
    base = (
        panel.genome_window_start
        + panel.input_start_offset
        - (panel.output_width - panel.input_width)
    )
    sources = np.asarray(base + columns, dtype=np.int32)
    targets = np.asarray(base + rows, dtype=np.int32)
    order = np.argsort(np.abs(effects), kind="stable")
    table = pa.Table.from_arrays(
        [
            pa.array(sources[order], type=pa.int32()),
            pa.array(targets[order], type=pa.int32()),
            pa.array(effects[order], type=pa.float32()),
        ],
        schema=LINK_SCHEMA,
    )
    if table.num_rows == 0:
        raise ValueError(f"No links passed the threshold for {panel.identifier}")
    return write_table_atomic(path, table)


def write_matrix(path: Path, panel: Panel, values: np.ndarray) -> int:
    """Write a dense PISA rectangle table in bounded row groups."""

    expected_shape = (panel.output_width, panel.input_width)
    if values.shape != expected_shape:
        raise ValueError(f"Wrong matrix shape for {panel.identifier}: {values.shape}")
    writer, temporary = parquet_writer(path, MATRIX_SCHEMA)
    count = 0
    try:
        input_positions = np.arange(
            panel.genome_window_start + panel.input_start_offset,
            panel.genome_window_start + panel.input_end_offset,
            dtype=np.int32,
        )
        for row_start in range(0, values.shape[0], 128):
            block = values[row_start : row_start + 128]
            output_positions = np.arange(
                panel.genome_window_start + panel.output_start_offset + row_start,
                panel.genome_window_start
                + panel.output_start_offset
                + row_start
                + block.shape[0],
                dtype=np.int32,
            )
            table = pa.Table.from_arrays(
                [
                    pa.array(np.tile(input_positions, block.shape[0]), pa.int32()),
                    pa.array(
                        np.repeat(output_positions, panel.input_width), pa.int32()
                    ),
                    pa.array(
                        np.asarray(block * LOG2_E, dtype=np.float32).reshape(-1),
                        pa.float32(),
                    ),
                ],
                schema=MATRIX_SCHEMA,
            )
            writer.write_table(table, row_group_size=table.num_rows)
            count += table.num_rows
        finish_parquet(writer, temporary, path)
    except Exception:
        try:
            writer.close()
        finally:
            temporary.unlink(missing_ok=True)
        raise
    return count


def read_bigwig_values(
    path: Path, chrom: str, start: int, end: int
) -> tuple[np.ndarray, np.ndarray]:
    """Read finite base-resolution values and their genomic positions."""

    with pyBigWig.open(str(path)) as bigwig:
        if chrom not in bigwig.chroms():
            raise ValueError(f"{chrom} is absent from {path}")
        values = np.asarray(bigwig.values(chrom, start, end), dtype=np.float32)
    positions = np.arange(start, end, dtype=np.int32)
    finite = np.isfinite(values)
    return positions[finite], values[finite]


def read_fasta_window(path: Path, start: int, end: int, padding: int) -> str:
    """Read a displayed interval from a padded PISA-input FASTA record.

    BPReveal names each record after the first output position, but the record
    itself begins ``padding`` bases earlier because it contains the full model
    input. Thus, the base for ``start`` is at ``sequence[padding]`` rather than
    at the beginning of the record.
    """

    if start < 0 or end <= start or padding < 0:
        raise ValueError("FASTA interval must be non-negative and non-empty")
    requested_length = end - start
    sequence_parts: list[str] | None = None
    with path.open(encoding="ascii") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            value = line.strip()
            if not value:
                continue
            if value.startswith(">"):
                if sequence_parts is not None:
                    break
                header = value[1:].split(maxsplit=1)[0]
                try:
                    record_start = int(header)
                except ValueError as error:
                    raise ValueError(
                        f"Non-numeric FASTA record at line {line_number} in {path}"
                    ) from error
                if record_start == start:
                    sequence_parts = []
                continue
            if sequence_parts is not None:
                sequence_parts.append(value.upper())

    if sequence_parts is None:
        raise ValueError(f"FASTA record starting at {start} is absent from {path}")
    sequence = "".join(sequence_parts)
    required_length = padding + requested_length
    if len(sequence) < required_length:
        raise ValueError(
            f"FASTA record at {start} is too short: {len(sequence)} < {required_length}"
        )
    result = sequence[padding:required_length]
    invalid = sorted(set(result) - set("ACGTN"))
    if invalid:
        raise ValueError(f"Invalid FASTA bases at {start}: {invalid}")
    return result


def write_tracks(path: Path, panel: Panel, paths: dict[str, Path]) -> int:
    """Write profile values and their reference bases for one panel."""

    position_parts: list[np.ndarray] = []
    label_parts: list[pa.Array] = []
    value_parts: list[np.ndarray] = []
    base_parts: list[pa.Array] = []
    for track in panel.tracks:
        if track.region == "input":
            start, end = panel.genomic_input_start, panel.genomic_input_end
        elif track.region == "output":
            start, end = panel.genomic_output_start, panel.genomic_output_end
        else:
            raise ValueError(f"Unknown track region: {track.region}")
        positions, values = read_bigwig_values(
            paths[track.member],
            panel.chrom,
            start,
            end,
        )
        if len(positions) == 0:
            raise ValueError(f"No finite values for {panel.identifier}/{track.label}")
        sequence = read_fasta_window(
            paths[panel.sequence_member], start, end, panel.sequence_padding
        )
        bases = [sequence[int(position) - start] for position in positions]
        position_parts.append(positions)
        value_parts.append(np.asarray(values * track.multiplier, dtype=np.float32))
        label_parts.append(pa.array([track.label] * len(positions), pa.string()))
        base_parts.append(pa.array(bases, pa.string()))
    table = pa.Table.from_arrays(
        [
            pa.array(np.concatenate(position_parts), pa.int32()),
            pa.concat_arrays(label_parts),
            pa.array(np.concatenate(value_parts), pa.float32()),
            pa.concat_arrays(base_parts),
        ],
        schema=TRACK_SCHEMA,
    )
    return write_table_atomic(path, table)


def bed_rows(
    path: Path, chrom: str, region_start: int, region_end: int
) -> Iterable[tuple[str, int, int, str, str, str]]:
    """Yield valid BED rows intersecting a locus."""

    with path.open(encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            if not line.strip() or line.startswith(("#", "track", "browser")):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 3:
                raise ValueError(f"Malformed BED row {line_number} in {path}")
            row_chrom = fields[0]
            start = int(fields[1])
            end = int(fields[2])
            if start < 0 or end <= start:
                raise ValueError(f"Invalid BED interval at row {line_number} in {path}")
            if row_chrom != chrom or end <= region_start or start >= region_end:
                continue
            yield (
                row_chrom,
                start,
                end,
                fields[3] if len(fields) > 3 else ".",
                fields[4] if len(fields) > 4 else ".",
                fields[5] if len(fields) > 5 else ".",
            )


def write_motifs(path: Path, panel: Panel, paths: dict[str, Path]) -> int:
    """Write annotations intersecting the displayed input locus."""

    rows = list(
        bed_rows(
            paths[panel.motifs_member],
            panel.chrom,
            panel.genomic_input_start,
            panel.genomic_input_end,
        )
    )
    columns = list(zip(*rows, strict=True)) if rows else [()] * 6
    table = pa.Table.from_arrays(
        [
            pa.array(columns[0], pa.string()),
            pa.array(columns[1], pa.int32()),
            pa.array(columns[2], pa.int32()),
            pa.array(columns[3], pa.string()),
            pa.array(columns[4], pa.string()),
            pa.array(columns[5], pa.string()),
        ],
        schema=MOTIF_SCHEMA,
    )
    return write_table_atomic(path, table)


def graph_slice(panel: Panel) -> tuple[int, int]:
    """Return the square BPReveal graph slice bounds before viewport trimming."""

    delta = panel.output_width - panel.input_width
    if delta < 0:
        raise ValueError("Graph output width must not be smaller than input width")
    return panel.input_start_offset - delta, panel.input_end_offset + delta


def panel_metadata(panel: Panel) -> dict[str, Any]:
    """Return visualization-facing metadata with genomic coordinates."""

    value: dict[str, Any] = {
        "assembly": panel.assembly,
        "chrom": panel.chrom,
        "inputStart": panel.genomic_input_start,
        "inputEnd": panel.genomic_input_end,
        "outputStart": panel.genome_window_start + panel.output_start_offset,
        "outputEnd": panel.genome_window_start + panel.output_end_offset,
        "colorSpan": panel.color_span * LOG2_E,
        "effectUnits": "log2FoldChange",
    }
    if panel.threshold is not None:
        start, end = graph_slice(panel)
        value.update(
            {
                "threshold": panel.threshold * LOG2_E,
                "linkDataStart": panel.genome_window_start + start,
                "linkDataEnd": panel.genome_window_start + end,
            }
        )
    return value


def write_json_atomic(path: Path, value: Any) -> None:
    """Write deterministic JSON atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    try:
        temporary.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def wrangle(paths: dict[str, Path], panels: Sequence[Panel] = PANELS) -> dict[str, int]:
    """Create every Parquet and metadata output."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for panel in panels:
        print(f"Preparing {panel.identifier}")
        counts[f"{panel.identifier}-tracks"] = write_tracks(
            OUTPUT_DIR / f"{panel.identifier}-tracks.parquet", panel, paths
        )
        counts[f"{panel.identifier}-motifs"] = write_motifs(
            OUTPUT_DIR / f"{panel.identifier}-motifs.parquet", panel, paths
        )

        if panel.threshold is not None:
            start, end = graph_slice(panel)
            values = read_combined_slice(
                paths, panel.pisa_members, start, end, start, end
            )
            link_name = (
                "fig2c-atac-links.parquet"
                if panel.identifier == "fig2cd-atac"
                else f"{panel.identifier}-links.parquet"
            )
            counts[link_name] = write_links(OUTPUT_DIR / link_name, panel, values)

        if panel.identifier in {"fig2cd-atac", "fig3b-h3k27ac"}:
            values = read_combined_slice(
                paths,
                panel.pisa_members,
                panel.output_start_offset,
                panel.output_end_offset,
                panel.input_start_offset,
                panel.input_end_offset,
            )
            matrix_name = (
                "fig2d-atac-matrix.parquet"
                if panel.identifier == "fig2cd-atac"
                else "fig3b-h3k27ac-matrix.parquet"
            )
            counts[matrix_name] = write_matrix(OUTPUT_DIR / matrix_name, panel, values)

    write_json_atomic(
        OUTPUT_DIR / "panels.json",
        {panel.identifier: panel_metadata(panel) for panel in panels},
    )
    return counts


def expected_outputs(
    panels: Sequence[Panel] = PANELS,
) -> dict[str, tuple[pa.Schema, int | None]]:
    """Return required Parquet schemas and fixed row counts."""

    contracts: dict[str, tuple[pa.Schema, int | None]] = {}
    for panel in panels:
        identifier = panel.identifier
        contracts[f"{identifier}-tracks.parquet"] = (TRACK_SCHEMA, None)
        contracts[f"{identifier}-motifs.parquet"] = (MOTIF_SCHEMA, None)
        if panel.threshold is not None:
            link_name = (
                "fig2c-atac-links.parquet"
                if identifier == "fig2cd-atac"
                else f"{identifier}-links.parquet"
            )
            contracts[link_name] = (LINK_SCHEMA, None)
        if identifier == "fig2cd-atac":
            contracts["fig2d-atac-matrix.parquet"] = (
                MATRIX_SCHEMA,
                panel.output_width * panel.input_width,
            )
        elif identifier == "fig3b-h3k27ac":
            contracts["fig3b-h3k27ac-matrix.parquet"] = (
                MATRIX_SCHEMA,
                panel.output_width * panel.input_width,
            )
    return contracts


def validate_accepted_output_identities(
    identities: dict[str, dict[str, Any]], provenance: dict[str, Any]
) -> None:
    """Require generated outputs to match the accepted provenance contract."""

    outputs = provenance.get("outputs")
    if not isinstance(outputs, dict):
        raise ValueError("provenance.json must contain an outputs object")

    accepted: dict[str, dict[str, Any]] = {}
    for identifier, value in outputs.items():
        if not isinstance(value, dict):
            raise ValueError(f"Invalid provenance output record: {identifier}")
        output_path = value.get("path")
        if not isinstance(output_path, str):
            raise ValueError(f"Missing output path in provenance record: {identifier}")
        relative_path = Path(output_path)
        if relative_path.is_absolute() or relative_path.parent != Path("output"):
            raise ValueError(f"Invalid output path in provenance record: {output_path}")
        if relative_path.name in accepted:
            raise ValueError(f"Duplicate output path in provenance: {output_path}")
        accepted[relative_path.name] = value

    if set(identities) != set(accepted):
        missing = sorted(set(accepted) - set(identities))
        unexpected = sorted(set(identities) - set(accepted))
        raise ValueError(
            "Generated outputs differ from the accepted contract: "
            f"missing={missing}, unexpected={unexpected}"
        )

    for name, actual in identities.items():
        expected = accepted[name]
        for key, actual_value in actual.items():
            if key not in expected:
                raise ValueError(f"Accepted {name} record is missing {key}")
            if expected[key] != actual_value:
                raise ValueError(
                    f"Accepted {name} {key} mismatch: "
                    f"{actual_value!r} != {expected[key]!r}"
                )


def verify_outputs(
    panels: Sequence[Panel] = PANELS,
) -> dict[str, dict[str, Any]]:
    """Validate output schemas and accepted provenance identities."""

    identities: dict[str, dict[str, Any]] = {}
    for name, (schema, fixed_count) in expected_outputs(panels).items():
        path = OUTPUT_DIR / name
        if not path.is_file():
            raise FileNotFoundError(path)
        parquet = pq.ParquetFile(path)
        actual_schema = parquet.schema_arrow
        if actual_schema != schema:
            raise ValueError(f"Unexpected schema for {name}: {actual_schema}")
        count = parquet.metadata.num_rows
        if fixed_count is not None and count != fixed_count:
            raise ValueError(f"Unexpected row count for {name}: {count}")
        if fixed_count is None and count == 0:
            raise ValueError(f"Unexpected empty output: {name}")
        identities[name] = {
            "fileSizeBytes": path.stat().st_size,
            "recordCount": count,
            "sha256": file_digest(path),
            "fields": actual_schema.names,
        }

    panels_path = OUTPUT_DIR / "panels.json"
    panel_metadata_value: Any = json.loads(panels_path.read_text(encoding="utf-8"))
    if not isinstance(panel_metadata_value, dict) or set(panel_metadata_value) != {
        panel.identifier for panel in panels
    }:
        raise ValueError("panels.json does not describe every selected panel")
    identities[panels_path.name] = {
        "fileSizeBytes": panels_path.stat().st_size,
        "sha256": file_digest(panels_path),
    }
    validate_accepted_output_identities(identities, load_provenance())
    return identities


def write_run_manifest(
    selected: dict[str, Path], outputs: dict[str, dict[str, Any]]
) -> None:
    """Record reproducibility identities locally without rewriting provenance."""

    write_json_atomic(
        RUN_MANIFEST,
        {
            "archiveMd5": source_record()["md5"],
            "selectedMembers": {
                identifier: {
                    "fileSizeBytes": path.stat().st_size,
                    "sha256": file_digest(path),
                }
                for identifier, path in sorted(selected.items())
            },
            "outputs": outputs,
        },
    )


def run_tests() -> int:
    """Run focused recipe tests in the PEP 723 environment."""

    import pytest

    return pytest.main([str(RECIPE_DIR / "tests"), "-q"])


def select_panels(value: str) -> tuple[Panel, ...]:
    """Resolve the CLI panel selector."""

    if value == "all":
        return PANELS
    return tuple(panel for panel in PANELS if panel.identifier == value)


def main() -> None:
    """Run the selected restartable stage."""

    args = parse_args()
    if args.test:
        raise SystemExit(run_tests())

    if args.stage in {"all", "download"}:
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if args.stage in {"all", "index", "extract", "wrangle"}:
        WORK_DIR.mkdir(parents=True, exist_ok=True)
    if args.stage in {"all", "wrangle"}:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    panels = select_panels(args.panel)
    members = members_for_panels(panels)

    if args.stage == "download":
        resolve_archive(args.archive, allow_download=True)
        return
    if args.stage == "index":
        archive = resolve_archive(args.archive, allow_download=False)
        write_archive_index(archive, ARCHIVE_INDEX, str(source_record()["md5"]))
        return
    if args.stage == "extract":
        archive = resolve_archive(args.archive, allow_download=False)
        extract_selected_members(archive, members)
        return
    if args.stage == "wrangle":
        selected = require_selected_members(members)
        wrangle(selected, panels)
        outputs = verify_outputs(panels)
        write_run_manifest(selected, outputs)
        return
    if args.stage == "verify":
        verify_outputs(panels)
        print("BPReveal PISA output verification passed")
        return

    archive = resolve_archive(args.archive, allow_download=True)
    selected = extract_selected_members(archive, members)
    wrangle(selected, panels)
    outputs = verify_outputs(panels)
    write_run_manifest(selected, outputs)
    print("BPReveal PISA preparation and verification passed")


if __name__ == "__main__":
    main()
