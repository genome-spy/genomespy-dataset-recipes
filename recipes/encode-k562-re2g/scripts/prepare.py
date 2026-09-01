#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0

# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""Prepare pinned ENCODE-rE2G K562 relations for the local GenomeSpy spec."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import platform
import shutil
import statistics
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

RECIPE_ID = "encode-k562-re2g"
ASSEMBLY = "GRCh38"
INITIAL_LOCUS = ("chr7", 106_800_000, 107_300_000)
USER_AGENT = "GenomeSpy dataset recipe encode-k562-re2g"

# GRCh38 primary assembly lengths (GCA_000001405.15).
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
CHROMOSOME_ORDER = {chrom: index for index, chrom in enumerate(CHROMOSOME_LENGTHS)}
INTERACTION_FIELDS = [
    "chrom",
    "elementStart",
    "elementEnd",
    "elementMid",
    "elementId",
    "elementClass",
    "geneTss",
    "geneId",
    "geneSymbol",
    "distanceToTss",
    "re2gScore",
    "abcScore",
]
OUTPUT_FILENAMES = {
    "interactions": "regulatory-element-gene-links.tsv.gz",
    "elements": "candidate-regulatory-elements.tsv.gz",
    "genes": "target-gene-tss.tsv.gz",
}


@dataclass(frozen=True)
class LockedSource:
    """One exact source artifact from provenance.json."""

    filename: str
    url: str
    file_size_bytes: int
    md5: str
    sha256: str


@dataclass(frozen=True)
class Interaction:
    """One normalized candidate-element-to-gene prediction."""

    chrom: str
    element_start: int
    element_end: int
    element_mid: float
    element_id: str
    element_class: str
    gene_tss: int
    gene_id: str
    gene_symbol: str
    distance_to_tss: float
    re2g_score: float
    abc_score: float

    def as_output(self) -> dict[str, object]:
        """Return the stable external field contract."""

        return {
            "chrom": self.chrom,
            "elementStart": self.element_start,
            "elementEnd": self.element_end,
            "elementMid": self.element_mid,
            "elementId": self.element_id,
            "elementClass": self.element_class,
            "geneTss": self.gene_tss,
            "geneId": self.gene_id,
            "geneSymbol": self.gene_symbol,
            "distanceToTss": self.distance_to_tss,
            "re2gScore": self.re2g_score,
            "abcScore": self.abc_score,
        }


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        help="Use this pinned source file instead of the ignored download cache.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify existing outputs against provenance without transforming.",
    )
    return parser.parse_args()


def file_hash(file: Path, algorithm: str = "sha256") -> str:
    """Return a hexadecimal checksum for a file."""

    with file.open("rb") as input_file:
        return hashlib.file_digest(input_file, algorithm).hexdigest()


def load_source(
    recipe_dir: Path,
) -> tuple[LockedSource, dict[str, Any], dict[str, Any], str]:
    """Load and validate the single pinned ENCODE source."""

    provenance = json.loads((recipe_dir / "provenance.json").read_bytes())
    sources = provenance.get("sources")
    if not isinstance(sources, list) or len(sources) != 1:
        raise ValueError("provenance.json must contain exactly one source.")
    source = sources[0]
    if not isinstance(source, dict):
        raise ValueError("The provenance source must be an object.")
    distribution = provenance.get("distribution")
    if not isinstance(distribution, dict):
        raise ValueError("Provenance must contain a distribution object.")
    release_id = provenance.get("releaseId")
    if not isinstance(release_id, str):
        raise ValueError("Provenance must contain a release ID.")

    locked = LockedSource(
        filename=str(source["filename"]),
        url=str(source["url"]),
        file_size_bytes=int(source["fileSizeBytes"]),
        md5=str(source["md5"]),
        sha256=str(source["sha256"]),
    )
    return locked, source, distribution, release_id


def validate_source(file: Path, source: LockedSource) -> None:
    """Require exact size, MD5, and SHA-256 identity."""

    if file.stat().st_size != source.file_size_bytes:
        raise ValueError(f"Source size does not match lock: {file}")
    if file_hash(file, "md5") != source.md5:
        raise ValueError(f"Source MD5 does not match lock: {file}")
    if file_hash(file) != source.sha256:
        raise ValueError(f"Source SHA-256 does not match lock: {file}")


def download_source(destination: Path, source: LockedSource) -> None:
    """Atomically download the exact source URL from provenance."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    request = Request(source.url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request) as response, temporary.open("wb") as output_file:
            shutil.copyfileobj(response, output_file)
        validate_source(temporary, source)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def resolve_source_path(
    recipe_dir: Path, explicit_source: Path | None, source: LockedSource
) -> Path:
    """Return an exact local source, downloading the locked artifact if needed."""

    if explicit_source is not None:
        source_path = explicit_source.resolve()
    else:
        source_path = recipe_dir / "download" / source.filename
        if not source_path.exists():
            download_source(source_path, source)
    if not source_path.is_file():
        raise FileNotFoundError(f"Pinned source is missing: {source_path}")
    validate_source(source_path, source)
    return source_path


def require_field(fieldnames: Iterable[str], *alternatives: str) -> str:
    """Return the first available source column from explicit alternatives."""

    available = set(fieldnames)
    for field in alternatives:
        if field in available:
            return field
    raise ValueError("Missing required source column: " + " or ".join(alternatives))


def parse_number(value: str, field: str, row_number: int) -> float:
    """Parse a finite numeric value with source context."""

    try:
        number = float(value)
    except ValueError as error:
        raise ValueError(
            f"Invalid {field} at source row {row_number}: {value}"
        ) from error
    if not math.isfinite(number):
        raise ValueError(f"Non-finite {field} at source row {row_number}: {value}")
    return number


def normalize_interactions(file: Path) -> tuple[list[Interaction], dict[str, Any]]:
    """Read, validate, normalize, and exactly deduplicate source interactions."""

    with gzip.open(file, "rt", encoding="utf-8", newline="") as input_file:
        header_line = input_file.readline().rstrip("\n")
        source_fields = header_line.removeprefix("#").split("\t")
        fields = {
            "chrom": require_field(source_fields, "chr", "chrom"),
            "start": require_field(source_fields, "start"),
            "end": require_field(source_fields, "end"),
            "element_id": require_field(source_fields, "name"),
            "element_class": require_field(source_fields, "class"),
            "gene_symbol": require_field(source_fields, "TargetGene"),
            "gene_id": require_field(
                source_fields, "TargetGeneEnsemblID", "TargetGeneEnsembl_ID"
            ),
            "gene_tss": require_field(source_fields, "TargetGeneTSS"),
            "distance": require_field(
                source_fields, "distanceToTSS.Feature", "distanceToTSS", "distance"
            ),
            "abc_score": require_field(source_fields, "ABC.Score.Feature", "ABC.Score"),
            "re2g_score": require_field(source_fields, "Score", "ENCODE-rE2G.Score"),
        }
        reader = csv.DictReader(input_file, fieldnames=source_fields, delimiter="\t")

        rows: list[Interaction] = []
        source_rows = 0
        half_base_midpoints = 0
        for row_number, raw in enumerate(reader, start=2):
            source_rows += 1
            chrom = raw[fields["chrom"]]
            start = int(raw[fields["start"]])
            end = int(raw[fields["end"]])
            gene_tss = int(raw[fields["gene_tss"]])
            element_mid = (start + end) / 2
            distance = parse_number(raw[fields["distance"]], "distance", row_number)
            re2g_score = parse_number(
                raw[fields["re2g_score"]], "rE2G score", row_number
            )
            abc_score = parse_number(raw[fields["abc_score"]], "ABC score", row_number)

            if chrom not in CHROMOSOME_LENGTHS:
                raise ValueError(f"Unexpected chromosome at source row {row_number}")
            if not 0 <= start < end <= CHROMOSOME_LENGTHS[chrom]:
                raise ValueError(f"Invalid element interval at source row {row_number}")
            if not 0 <= gene_tss < CHROMOSOME_LENGTHS[chrom]:
                raise ValueError(f"Invalid gene TSS at source row {row_number}")
            if distance != abs(gene_tss - element_mid):
                raise ValueError(f"Distance mismatch at source row {row_number}")
            if not 0 <= re2g_score <= 1 or not 0 <= abc_score <= 1:
                raise ValueError(f"Score outside [0, 1] at source row {row_number}")

            gene_id = raw[fields["gene_id"]]
            gene_symbol = raw[fields["gene_symbol"]]
            if not gene_id.startswith("ENSG") or not gene_symbol:
                raise ValueError(
                    f"Unexpected gene identifier at source row {row_number}"
                )
            if element_mid % 1:
                half_base_midpoints += 1

            rows.append(
                Interaction(
                    chrom=chrom,
                    element_start=start,
                    element_end=end,
                    element_mid=element_mid,
                    element_id=raw[fields["element_id"]],
                    element_class=raw[fields["element_class"]],
                    gene_tss=gene_tss,
                    gene_id=gene_id,
                    gene_symbol=gene_symbol,
                    distance_to_tss=distance,
                    re2g_score=re2g_score,
                    abc_score=abc_score,
                )
            )

    unique_rows = set(rows)
    sorted_rows = sorted(
        unique_rows,
        key=lambda row: (
            CHROMOSOME_ORDER[row.chrom],
            row.element_start,
            row.element_end,
            row.gene_tss,
            row.gene_id,
            row.re2g_score,
            row.abc_score,
        ),
    )
    annotations_by_gene_id: dict[str, set[tuple[str, int, str]]] = {}
    for row in sorted_rows:
        annotations_by_gene_id.setdefault(row.gene_id, set()).add(
            (row.chrom, row.gene_tss, row.gene_symbol)
        )
    conflicts = {
        gene_id: [
            {"chrom": chrom, "geneTss": gene_tss, "geneSymbol": gene_symbol}
            for chrom, gene_tss, gene_symbol in sorted(annotations)
        ]
        for gene_id, annotations in sorted(annotations_by_gene_id.items())
        if len(annotations) > 1
    }
    stats: dict[str, Any] = {
        "selectedColumns": fields,
        "sourceRows": source_rows,
        "processedRows": len(sorted_rows),
        "exactDuplicateRowsRemoved": source_rows - len(sorted_rows),
        "halfBaseElementMidpoints": half_base_midpoints,
        "elementClasses": dict(
            sorted(Counter(row.element_class for row in sorted_rows).items())
        ),
        "scoreRanges": {
            "re2gScore": [
                min(row.re2g_score for row in sorted_rows),
                max(row.re2g_score for row in sorted_rows),
            ],
            "abcScore": [
                min(row.abc_score for row in sorted_rows),
                max(row.abc_score for row in sorted_rows),
            ],
        },
        "geneIdAnnotationConflicts": conflicts,
    }
    return sorted_rows, stats


def format_number(value: object) -> object:
    """Format numeric values compactly and deterministically."""

    if isinstance(value, (int, float)):
        return str(int(value)) if float(value).is_integer() else str(value)
    return value


def write_tsv_gz(
    destination: Path, fieldnames: list[str], rows: Iterable[Mapping[str, object]]
) -> int:
    """Atomically write deterministic gzip-compressed TSV data."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    count = 0
    try:
        with temporary.open("wb") as raw_file:
            with gzip.GzipFile(
                filename="", mode="wb", fileobj=raw_file, mtime=0
            ) as gzip_file:
                with io.TextIOWrapper(
                    gzip_file, encoding="utf-8", newline=""
                ) as output_file:
                    writer = csv.DictWriter(
                        output_file,
                        fieldnames=fieldnames,
                        delimiter="\t",
                        lineterminator="\n",
                    )
                    writer.writeheader()
                    for row in rows:
                        writer.writerow(
                            {
                                field: format_number(value)
                                for field, value in row.items()
                            }
                        )
                        count += 1
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return count


def derive_elements(interactions: Iterable[Interaction]) -> list[dict[str, object]]:
    """Return unique candidate elements, requiring consistent annotations."""

    elements: dict[tuple[str, int, int, str], dict[str, object]] = {}
    for row in interactions:
        key = row.chrom, row.element_start, row.element_end, row.element_id
        element = {
            "chrom": row.chrom,
            "elementStart": row.element_start,
            "elementEnd": row.element_end,
            "elementMid": row.element_mid,
            "elementId": row.element_id,
            "elementClass": row.element_class,
        }
        if key in elements and elements[key] != element:
            raise ValueError(f"Conflicting annotations for {row.element_id}")
        elements[key] = element
    return list(elements.values())


def derive_genes(interactions: Iterable[Interaction]) -> list[dict[str, object]]:
    """Return unique target-gene TSS endpoints."""

    genes: dict[tuple[str, int, str], dict[str, object]] = {}
    for row in interactions:
        key = row.chrom, row.gene_tss, row.gene_id
        gene = {
            "chrom": row.chrom,
            "geneTss": row.gene_tss,
            "geneId": row.gene_id,
            "geneSymbol": row.gene_symbol,
        }
        if key in genes and genes[key] != gene:
            raise ValueError(f"Conflicting symbols for target gene {row.gene_id}")
        genes[key] = gene
    return list(genes.values())


def locus_stats(interactions: Iterable[Interaction]) -> dict[str, object]:
    """Summarize links whose spans intersect the configured initial locus."""

    chrom, start, end = INITIAL_LOCUS
    visible = [
        row
        for row in interactions
        if row.chrom == chrom
        and min(row.element_mid, row.gene_tss) < end
        and max(row.element_mid, row.gene_tss) >= start
    ]
    distances = sorted(row.distance_to_tss for row in visible)
    return {
        "chrom": chrom,
        "start": start,
        "end": end,
        "visibleLinks": len(visible),
        "uniqueElements": len(
            {(row.element_start, row.element_end, row.element_id) for row in visible}
        ),
        "uniqueGenes": len({(row.gene_tss, row.gene_id) for row in visible}),
        "distanceToTss": {
            "minimum": min(distances),
            "median": statistics.median(distances),
            "maximum": max(distances),
        },
    }


def gzip_record_count(file: Path) -> int:
    """Return the number of data rows in a gzip-compressed text table."""

    with gzip.open(file, "rt", encoding="utf-8") as input_file:
        line_count = sum(1 for _line in input_file)
    return max(0, line_count - 1)


def write_provenance(
    recipe_dir: Path,
    release_id: str,
    source_record: Mapping[str, Any],
    distribution_record: Mapping[str, Any],
    outputs: Mapping[str, Path],
    output_rows: Mapping[str, int],
    stats: Mapping[str, Any],
    initial_locus: Mapping[str, object],
) -> None:
    """Write compact accepted-run provenance without local paths or data rows."""

    output_records = {
        name: {
            "path": "output/" + file.name,
            "fileSizeBytes": file.stat().st_size,
            "sha256": file_hash(file),
            "recordCount": output_rows[name],
        }
        for name, file in outputs.items()
    }
    distribution = dict(distribution_record)
    distribution["artifacts"] = {
        record["path"]: {
            "fileSizeBytes": record["fileSizeBytes"],
            "sha256": record["sha256"],
        }
        for record in output_records.values()
    }
    provenance = {
        "schemaVersion": 2,
        "releaseId": release_id,
        "recipeId": RECIPE_ID,
        "distribution": distribution,
        "sources": [dict(source_record)],
        "tools": {"python": platform.python_version()},
        "transformations": {
            "coordinates": (
                "Element intervals remain zero-based and half-open; gene TSS "
                "values remain zero-based points; elementMid = "
                "(elementStart + elementEnd) / 2."
            ),
            "duplicates": (
                "Remove only rows identical across all 12 interaction fields."
            ),
            "threshold": (
                "No added threshold; the released source is already thresholded."
            ),
            "sorting": (
                "GRCh38 primary chromosome order, then element and gene "
                "coordinates, IDs, and scores."
            ),
        },
        "outputs": output_records,
        "validation": {
            "exactDuplicateRowsRemoved": stats["exactDuplicateRowsRemoved"],
            "halfBaseElementMidpoints": stats["halfBaseElementMidpoints"],
            "elementClasses": stats["elementClasses"],
            "re2gScoreRange": stats["scoreRanges"]["re2gScore"],
            "abcScoreRange": stats["scoreRanges"]["abcScore"],
            "geneIdAnnotationConflictIds": sorted(stats["geneIdAnnotationConflicts"]),
            "initialLocus": {
                "domain": (
                    f"{initial_locus['chrom']}:{initial_locus['start']}-"
                    f"{initial_locus['end']}"
                ),
                "visibleLinks": initial_locus["visibleLinks"],
                "uniqueElements": initial_locus["uniqueElements"],
                "uniqueGenes": initial_locus["uniqueGenes"],
            },
        },
    }
    destination = recipe_dir / "provenance.json"
    temporary = destination.with_name(destination.name + ".part")
    try:
        temporary.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def verify_outputs(recipe_dir: Path) -> None:
    """Verify output fingerprints against committed provenance."""

    provenance_path = recipe_dir / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if provenance.get("recipeId") != RECIPE_ID:
        raise ValueError("Provenance recipe ID does not match.")
    outputs = provenance.get("outputs")
    if not isinstance(outputs, dict):
        raise ValueError("Provenance outputs must be an object.")
    for details in outputs.values():
        if not isinstance(details, dict):
            raise ValueError("Provenance output details must be objects.")
        relative = details.get("path")
        if not isinstance(relative, str) or not relative.startswith("output/"):
            raise ValueError("Invalid provenance output path.")
        file = recipe_dir / relative
        if not file.is_file():
            raise FileNotFoundError(f"Expected output is missing: {relative}")
        if file.stat().st_size != details.get("fileSizeBytes"):
            raise ValueError(f"Output size changed: {relative}")
        if file_hash(file) != details.get("sha256"):
            raise ValueError(f"Output checksum changed: {relative}")
        if gzip_record_count(file) != details.get("recordCount"):
            raise ValueError(f"Output record count changed: {relative}")


def main() -> None:
    """Prepare or verify the pinned recipe outputs."""

    args = parse_args()
    recipe_dir = Path(__file__).resolve().parents[1]
    source, source_record, distribution_record, release_id = load_source(recipe_dir)
    if args.verify_only:
        verify_outputs(recipe_dir)
        print("Verified accepted outputs.")
        return

    source_path = resolve_source_path(recipe_dir, args.source, source)
    interactions, stats = normalize_interactions(source_path)
    elements = derive_elements(interactions)
    genes = derive_genes(interactions)
    output_dir = recipe_dir / "output"
    outputs = {
        name: output_dir / filename for name, filename in OUTPUT_FILENAMES.items()
    }
    output_rows = {
        "interactions": write_tsv_gz(
            outputs["interactions"],
            INTERACTION_FIELDS,
            (row.as_output() for row in interactions),
        ),
        "elements": write_tsv_gz(
            outputs["elements"],
            [
                "chrom",
                "elementStart",
                "elementEnd",
                "elementMid",
                "elementId",
                "elementClass",
            ],
            elements,
        ),
        "genes": write_tsv_gz(
            outputs["genes"],
            ["chrom", "geneTss", "geneId", "geneSymbol"],
            genes,
        ),
    }
    write_provenance(
        recipe_dir,
        release_id,
        source_record,
        distribution_record,
        outputs,
        output_rows,
        stats,
        locus_stats(interactions),
    )
    verify_outputs(recipe_dir)
    print("Prepared and verified pinned outputs.")


if __name__ == "__main__":
    main()
