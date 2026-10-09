#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0

# /// script
# requires-python = ">=3.12"
# dependencies = ["pysam==0.23.3"]
# ///

"""Prepare RNF7 direct-RNA coverage, alignments, sequence, and m6A sites."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import shutil
import tarfile
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import pysam  # type: ignore[import-not-found]

RECIPE_DIR = Path(__file__).resolve().parents[1]
DOWNLOAD_DIR = RECIPE_DIR / "download"
WORK_DIR = RECIPE_DIR / "work"
OUTPUT_DIR = RECIPE_DIR / "output"
PROVENANCE_PATH = RECIPE_DIR / "provenance.json"
OUTPUT_PATH = OUTPUT_DIR / "rnf7-direct-rna.json.gz"
TRANSCRIPT = "ENST00000273480.3"
SITE_TRANSCRIPT = "ENST00000273480"
GENE_ID = "ENSG00000114125"
DISPLAY_END = 920
USER_AGENT = "GenomeSpy dataset recipe xpore-hek293t-rnf7-m6a"
CONDITIONS = (
    (
        "WT",
        "Wild type",
        "demo/data/HEK293T-WT-rep1/bamtx/aligned.bam",
    ),
    (
        "KO",
        "METTL3 knockout",
        "demo/data/HEK293T-METTL3-KO-rep1/bamtx/aligned.bam",
    ),
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo-archive", type=Path)
    parser.add_argument("--calls-table", type=Path)
    parser.add_argument("--reference-exon-1", type=Path)
    parser.add_argument("--reference-exon-2", type=Path)
    parser.add_argument("--reference-exon-3", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    return parser.parse_args()


def load_provenance() -> dict[str, Any]:
    """Load the accepted-run record."""
    value = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("provenance.json must contain an object")
    return value


def digest(path: Path, algorithm: str = "sha256") -> str:
    """Return a streaming file digest."""
    value = hashlib.new(algorithm)
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def verify_file(path: Path, record: dict[str, Any]) -> None:
    """Require exact size, MD5 when present, and SHA-256."""
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size != int(record["fileSizeBytes"]):
        raise ValueError(f"File size does not match provenance: {path}")
    if "md5" in record and digest(path, "md5") != record["md5"]:
        raise ValueError(f"MD5 does not match provenance: {path}")
    if digest(path) != record["sha256"]:
        raise ValueError(f"SHA-256 does not match provenance: {path}")


def download(record: dict[str, Any], destination: Path) -> Path:
    """Download and verify one pinned source."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        temporary = destination.with_name(destination.name + ".part")
        headers = {"User-Agent": USER_AGENT, **record.get("headers", {})}
        request = Request(str(record["url"]), headers=headers)
        try:
            with urlopen(request) as response, temporary.open("wb") as output_file:
                shutil.copyfileobj(response, output_file)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    verify_file(destination, record)
    return destination


def resolve_source(
    explicit: Path | None, record: dict[str, Any], default_name: str
) -> Path:
    """Resolve an explicit source or the verified download cache."""
    if explicit is not None:
        path = explicit.expanduser().resolve()
        verify_file(path, record)
        return path
    return download(record, DOWNLOAD_DIR / default_name)


def extract_members(archive: Path, source: dict[str, Any]) -> dict[str, Path]:
    """Extract and verify the selected regular-file members."""
    extracted: dict[str, Path] = {}
    with tarfile.open(archive, "r:gz") as input_archive:
        for member_name, record in source["members"].items():
            member = input_archive.getmember(member_name)
            if not member.isfile():
                raise ValueError(f"Archive member is not a regular file: {member_name}")
            input_file = input_archive.extractfile(member)
            if input_file is None:
                raise ValueError(f"Cannot read archive member: {member_name}")
            destination = WORK_DIR / member_name
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(destination.name + ".part")
            try:
                with input_file, temporary.open("wb") as output_file:
                    shutil.copyfileobj(input_file, output_file)
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)
            verify_file(destination, record)
            extracted[member_name] = destination
    return extracted


def primary_reads(bam: pysam.AlignmentFile) -> list[pysam.AlignedSegment]:
    """Return mapped primary RNF7 alignments in stable order."""
    reads = [
        read
        for read in bam.fetch(TRANSCRIPT, 0, DISPLAY_END)
        if not read.is_unmapped and not read.is_secondary and not read.is_supplementary
    ]
    return sorted(
        reads,
        key=lambda read: (
            read.reference_start,
            read.reference_end or -1,
            read.query_name,
        ),
    )


def assign_lanes(reads: list[pysam.AlignedSegment]) -> list[int]:
    """Pack sorted alignments into the first available non-overlapping lane."""
    lane_ends: list[int] = []
    lanes: list[int] = []
    for read in reads:
        start = read.reference_start
        end = read.reference_end or start
        for lane, lane_end in enumerate(lane_ends):
            if lane_end <= start:
                lane_ends[lane] = end
                lanes.append(lane)
                break
        else:
            lanes.append(len(lane_ends))
            lane_ends.append(end)
    return lanes


def alignment_events(
    read: pysam.AlignedSegment,
    *,
    condition: str,
    condition_label: str,
    read_label: str,
    lane: int,
    reference: str,
) -> list[dict[str, Any]]:
    """Expand mismatches and CIGAR operations into displayable read events."""
    rows: list[dict[str, Any]] = []
    query = (read.query_sequence or "").upper()
    qualities = read.query_qualities
    reference_offset = read.reference_start
    query_offset = 0

    def append_event(**values: Any) -> None:
        rows.append(
            {
                "condition": condition,
                "conditionLabel": condition_label,
                "read": read_label,
                "lane": lane,
                **values,
            }
        )

    for operation, length in read.cigartuples or []:
        if operation in (0, 7, 8):
            if operation != 7:
                for offset in range(length):
                    position = reference_offset + offset
                    read_offset = query_offset + offset
                    if (
                        0 <= position < DISPLAY_END
                        and read_offset < len(query)
                        and query[read_offset] != reference[position]
                    ):
                        append_event(
                            eventType="mismatch",
                            start=position,
                            end=position + 1,
                            length=1,
                            base=query[read_offset],
                            refBase=reference[position],
                            baseQuality=(
                                qualities[read_offset]
                                if qualities is not None
                                else None
                            ),
                        )
            reference_offset += length
            query_offset += length
        elif operation == 1:
            if 0 <= reference_offset <= DISPLAY_END:
                append_event(
                    eventType="insertion",
                    start=reference_offset,
                    end=reference_offset,
                    length=length,
                    insertedSequence=query[query_offset : query_offset + length],
                )
            query_offset += length
        elif operation in (2, 3):
            start = max(0, reference_offset)
            end = min(DISPLAY_END, reference_offset + length)
            if end > start:
                append_event(
                    eventType="deletion" if operation == 2 else "skip",
                    start=start,
                    end=end,
                    length=length,
                )
            reference_offset += length
        elif operation == 4:
            if 0 <= reference_offset <= DISPLAY_END:
                append_event(
                    eventType="softClip",
                    start=reference_offset,
                    end=reference_offset,
                    length=length,
                )
            query_offset += length
        elif operation not in (5, 6):
            raise ValueError(f"Unsupported CIGAR operation {operation}")
    return rows


def alignment_tables(
    extracted: dict[str, Path], reference: str
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, int],
]:
    """Create coverage, read-span, and alignment-event tables."""
    coverage_rows: list[dict[str, Any]] = []
    read_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for condition, label, member_name in CONDITIONS:
        path = extracted[member_name]
        with pysam.AlignmentFile(path, "rb") as bam:
            if bam.get_reference_length(TRANSCRIPT) != 2763:
                raise ValueError(f"Unexpected RNF7 transcript length in {path}")
            reads = primary_reads(bam)
        counts[condition] = len(reads)
        depth = [0] * DISPLAY_END
        lanes = assign_lanes(reads)
        lane_count = max(lanes, default=-1) + 1
        for index, (read, lane) in enumerate(zip(reads, lanes, strict=True), start=1):
            start = max(0, read.reference_start)
            end = min(DISPLAY_END, read.reference_end or start)
            if end <= start:
                continue
            read_label = f"{condition}-{index:03d}"
            read_rows.append(
                {
                    "condition": condition,
                    "conditionLabel": label,
                    "read": read_label,
                    "start": start,
                    "end": end,
                    "lane": lane,
                    "overviewY": (
                        (lane + 0.5) / lane_count * 0.44
                        if condition == "WT"
                        else 0.56 + (lane + 0.5) / lane_count * 0.44
                    ),
                    "mapq": read.mapping_quality,
                    "queryLength": read.query_length,
                    "referenceSpan": end - start,
                }
            )
            event_rows.extend(
                alignment_events(
                    read,
                    condition=condition,
                    condition_label=label,
                    read_label=read_label,
                    lane=lane,
                    reference=reference,
                )
            )
            for position in read.get_reference_positions(full_length=False):
                if 0 <= position < DISPLAY_END:
                    depth[position] += 1
        for position, value in enumerate(depth):
            coverage_rows.append(
                {
                    "condition": condition,
                    "conditionLabel": label,
                    "position": position,
                    "coverage": value,
                    "coverageFraction": value / len(reads),
                }
            )
    return coverage_rows, read_rows, event_rows, counts


def reference_sequence(paths: list[Path]) -> tuple[str, list[dict[str, Any]]]:
    """Load the three GRCh38 exon sequences as one transcript sequence."""
    sequence = "".join(path.read_text(encoding="utf-8").strip() for path in paths)
    sequence = sequence.upper()
    if len(sequence) != 2763 or set(sequence) - set("ACGTN"):
        raise ValueError("Unexpected RNF7 transcript reference sequence")
    return sequence, [
        {"position": position, "base": base}
        for position, base in enumerate(sequence[:DISPLAY_END])
    ]


def parse_attributes(value: str) -> dict[str, str]:
    """Parse the simple quoted attribute form used by the demo GTF."""
    attributes: dict[str, str] = {}
    for field in value.rstrip(";").split("; "):
        key, raw_value = field.split(" ", 1)
        attributes[key] = raw_value.strip('"')
    return attributes


def exon_table(gtf_path: Path) -> list[dict[str, Any]]:
    """Map RNF7 exons to cumulative transcript coordinates."""
    genomic: list[tuple[int, int, int]] = []
    with gtf_path.open(encoding="utf-8") as input_file:
        for line in input_file:
            if line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 9 or fields[2] != "exon":
                continue
            attributes = parse_attributes(fields[8])
            if attributes.get("transcript_id") != SITE_TRANSCRIPT:
                continue
            genomic.append(
                (int(attributes["exon_number"]), int(fields[3]), int(fields[4]))
            )
    genomic.sort()
    transcript_start = 0
    rows: list[dict[str, Any]] = []
    for exon, genomic_start, genomic_end in genomic:
        length = genomic_end - genomic_start + 1
        transcript_end = transcript_start + length
        display_start = max(0, transcript_start)
        display_end = min(DISPLAY_END, transcript_end)
        rows.append(
            {
                "exon": exon,
                "start": transcript_start,
                "end": transcript_end,
                "displayStart": display_start,
                "displayEnd": display_end,
                "displayCenter": (display_start + display_end) / 2,
                "genomicStart": genomic_start,
                "genomicEnd": genomic_end,
            }
        )
        transcript_start = transcript_end
    if transcript_start != 2763 or len(rows) != 3:
        raise ValueError("Unexpected RNF7 exon structure")
    return rows


def site_table(calls_path: Path) -> list[dict[str, Any]]:
    """Select and reshape the published RNF7 m6Anet calls."""
    rows: list[dict[str, Any]] = []
    with calls_path.open(encoding="utf-8", newline="") as input_file:
        for source_row in csv.DictReader(input_file):
            if (
                source_row["gene_id"] != GENE_ID
                or source_row["transcript_id"] != SITE_TRANSCRIPT
            ):
                continue
            position = int(source_row["transcript_position"])
            wt = float(source_row["probability_modified_wt"])
            ko = float(source_row["probability_modified_ko"])
            for condition, label, probability in (
                ("WT", "Wild type", wt),
                ("KO", "METTL3 knockout", ko),
            ):
                rows.append(
                    {
                        "site": f"RNF7:{position}",
                        "position": position,
                        "genomicPosition": int(source_row["genomic_position"]),
                        "kmer": source_row["kmer"],
                        "condition": condition,
                        "conditionLabel": label,
                        "probability": probability,
                        "difference": wt - ko,
                        "highConfidence": probability >= 0.9,
                    }
                )
    rows.sort(key=lambda row: (row["position"], row["condition"]))
    if len(rows) != 24:
        raise ValueError(f"Expected 24 long-form site rows, found {len(rows)}")
    return rows


def write_bundle(value: dict[str, Any], destination: Path) -> None:
    """Write stable compact JSON in a deterministic gzip stream."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    payload = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    try:
        with temporary.open("wb") as raw_file:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw_file, mtime=0) as gz:
                gz.write(payload)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def validate_bundle(bundle: dict[str, Any]) -> None:
    """Validate the scientific and display contract."""
    if bundle["metadata"]["readCounts"] != {"KO": 151, "WT": 77}:
        raise ValueError(
            f"Unexpected RNF7 read counts: {bundle['metadata']['readCounts']}"
        )
    sites = bundle["sites"]
    prominent = {
        row["condition"]: row["probability"] for row in sites if row["position"] == 614
    }
    if prominent != {"KO": 0.3039894700050354, "WT": 0.9885296821594238}:
        raise ValueError("Unexpected RNF7 position-614 probabilities")
    for condition, read_count in bundle["metadata"]["readCounts"].items():
        coverage = [row for row in bundle["coverage"] if row["condition"] == condition]
        if len(coverage) != DISPLAY_END:
            raise ValueError(f"Unexpected coverage length for {condition}")
        if max(row["coverage"] for row in coverage) > read_count:
            raise ValueError(f"Coverage exceeds read count for {condition}")
    if len(bundle["sequence"]) != DISPLAY_END:
        raise ValueError("Unexpected displayed reference-sequence length")
    event_counts = {
        event_type: sum(row["eventType"] == event_type for row in bundle["events"])
        for event_type in {row["eventType"] for row in bundle["events"]}
    }
    expected_event_counts = {
        "deletion": 6695,
        "insertion": 4280,
        "mismatch": 7282,
        "skip": 16,
        "softClip": 429,
    }
    if event_counts != expected_event_counts:
        raise ValueError(f"Unexpected alignment event counts: {event_counts}")


def verify_output(provenance: dict[str, Any]) -> None:
    """Verify the accepted output identity and content contract."""
    record = provenance["outputs"]["bundle"]
    verify_file(OUTPUT_PATH, record)
    with gzip.open(OUTPUT_PATH, "rt", encoding="utf-8") as input_file:
        bundle = json.load(input_file)
    validate_bundle(bundle)


def main() -> None:
    """Prepare or verify the accepted RNF7 output."""
    args = parse_args()
    provenance = load_provenance()
    if args.verify_only:
        verify_output(provenance)
        return
    sources = {source["id"]: source for source in provenance["sources"]}
    demo = resolve_source(args.demo_archive, sources["xpore-demo"], "demo.tar.gz")
    calls = resolve_source(
        args.calls_table,
        sources["m6anet-supplementary-table-6"],
        "m6anet-supplementary-table-6.csv",
    )
    reference_paths = [
        resolve_source(
            getattr(args, f"reference_exon_{exon}"),
            sources[f"ensembl-rnf7-exon-{exon}"],
            f"rnf7-exon-{exon}.txt",
        )
        for exon in (1, 2, 3)
    ]
    extracted = extract_members(demo, sources["xpore-demo"])
    reference, sequence = reference_sequence(reference_paths)
    coverage, reads, events, read_counts = alignment_tables(extracted, reference)
    bundle = {
        "metadata": {
            "gene": "RNF7",
            "geneId": GENE_ID,
            "transcriptId": TRANSCRIPT,
            "displayStart": 0,
            "displayEnd": DISPLAY_END,
            "readCounts": read_counts,
        },
        "coverage": coverage,
        "reads": reads,
        "events": events,
        "sequence": sequence,
        "sites": site_table(calls),
        "exons": exon_table(extracted["demo/demo.gtf"]),
    }
    validate_bundle(bundle)
    write_bundle(bundle, OUTPUT_PATH)
    if provenance["outputs"]:
        verify_output(provenance)


if __name__ == "__main__":
    main()
