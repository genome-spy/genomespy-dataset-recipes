#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0

# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""Prepare recurrent TCGA-BRCA PIK3CA mutations and protein domains."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import re
import shutil
from collections import defaultdict
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

RECIPE_DIR = Path(__file__).resolve().parents[1]
PROVENANCE_PATH = RECIPE_DIR / "provenance.json"
DEFAULT_MAF_DIR = RECIPE_DIR / "download" / "gdc"
DEFAULT_UNIPROT_PATH = RECIPE_DIR / "download" / "uniprot-P42336.json"
OUTPUT_DIR = RECIPE_DIR / "output"
USER_AGENT = "GenomeSpy dataset recipe tcga-brca-gdc-pik3ca-mutations"
MUTATION_FIELDS = (
    "position",
    "mutation",
    "sampleCount",
    "variantClass",
    "sourceProteinPosition",
)
DOMAIN_FIELDS = ("start", "end", "label", "description")
REQUIRED_MAF_FIELDS = {
    "Hugo_Symbol",
    "NCBI_Build",
    "Variant_Classification",
    "Tumor_Sample_Barcode",
    "HGVSp_Short",
    "Transcript_ID",
    "Protein_position",
}


@dataclass(frozen=True)
class GdcFile:
    """One exact GDC input file."""

    file_id: str
    filename: str
    size: int
    md5: str


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--maf-directory",
        type=Path,
        default=DEFAULT_MAF_DIR,
        help="Directory containing <GDC UUID>/<filename> inputs.",
    )
    parser.add_argument(
        "--uniprot",
        type=Path,
        default=DEFAULT_UNIPROT_PATH,
        help="Path to the accepted UniProt P42336 JSON record.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify existing outputs without reading or downloading inputs.",
    )
    return parser.parse_args()


def load_provenance() -> dict[str, Any]:
    """Load the committed accepted-run record."""

    value: Any = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("provenance.json must contain an object.")
    return value


def source_by_id(provenance: dict[str, Any], identifier: str) -> dict[str, Any]:
    """Return one named source record."""

    sources = provenance.get("sources")
    if not isinstance(sources, list):
        raise ValueError("provenance.json sources must be a list.")
    matches = [source for source in sources if source.get("id") == identifier]
    if len(matches) != 1 or not isinstance(matches[0], dict):
        raise ValueError(f"Expected exactly one provenance source {identifier}.")
    return matches[0]


def digest(path: Path, algorithm: str) -> str:
    """Return a streaming hexadecimal digest."""

    value = hashlib.new(algorithm)
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def gdc_files(source: dict[str, Any]) -> list[GdcFile]:
    """Parse and validate the compact GDC manifest."""

    values = source.get("files")
    if not isinstance(values, list) or not values:
        raise ValueError("The GDC source must contain a non-empty file list.")
    locks = [
        GdcFile(
            file_id=str(value["fileId"]),
            filename=str(value["filename"]),
            size=int(value["fileSizeBytes"]),
            md5=str(value["md5"]),
        )
        for value in values
    ]
    if len(locks) != int(source["fileCount"]):
        raise ValueError("GDC file count does not match provenance.")
    if sum(lock.size for lock in locks) != int(source["totalFileSizeBytes"]):
        raise ValueError("GDC byte count does not match provenance.")
    if len({lock.file_id for lock in locks}) != len(locks):
        raise ValueError("Duplicate GDC file UUID in provenance.")
    compact = "".join(
        f"{lock.file_id}\t{lock.filename}\t{lock.size}\t{lock.md5}\n" for lock in locks
    ).encode()
    if hashlib.sha256(compact).hexdigest() != source["compactManifestSha256"]:
        raise ValueError("Compact GDC manifest checksum does not match provenance.")
    return locks


def validate_file(path: Path, size: int, algorithm: str, checksum: str) -> None:
    """Require one file to match its accepted identity."""

    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size != size:
        raise ValueError(f"File size does not match provenance: {path}")
    if digest(path, algorithm).lower() != checksum.lower():
        raise ValueError(f"{algorithm.upper()} does not match provenance: {path}")


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


def resolve_gdc_inputs(
    directory: Path, source: dict[str, Any], locks: list[GdcFile]
) -> list[Path]:
    """Download missing default inputs and validate every pinned GDC file."""

    directory = directory.expanduser().resolve()
    paths = [directory / lock.file_id / lock.filename for lock in locks]
    missing = [
        (lock, path)
        for lock, path in zip(locks, paths, strict=True)
        if not path.exists()
    ]
    if missing and directory != DEFAULT_MAF_DIR.resolve():
        raise FileNotFoundError(f"Missing explicit GDC input: {missing[0][1]}")

    endpoint = str(source["dataEndpoint"])

    def fetch(item: tuple[GdcFile, Path]) -> None:
        lock, path = item
        download(endpoint + lock.file_id, path)
        validate_file(path, lock.size, "md5", lock.md5)

    if missing:
        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(fetch, missing))
    for lock, path in zip(locks, paths, strict=True):
        validate_file(path, lock.size, "md5", lock.md5)
    return paths


def resolve_uniprot(path: Path, source: dict[str, Any]) -> Path:
    """Download the default UniProt input when missing, then verify it."""

    path = path.expanduser().resolve()
    if not path.exists():
        if path != DEFAULT_UNIPROT_PATH.resolve():
            raise FileNotFoundError(f"Missing explicit UniProt input: {path}")
        download(str(source["url"]), path)
    validate_file(path, int(source["fileSizeBytes"]), "sha256", str(source["sha256"]))
    return path


def maf_rows(paths: Iterable[Path]) -> Iterable[dict[str, str]]:
    """Yield rows from verified GDC MAF inputs in manifest order."""

    for path in paths:
        with gzip.open(path, mode="rt", encoding="utf-8", newline="") as input_file:
            data_lines = (line for line in input_file if not line.startswith("#"))
            reader = csv.DictReader(data_lines, delimiter="\t")
            if reader.fieldnames is None or not REQUIRED_MAF_FIELDS.issubset(
                reader.fieldnames
            ):
                raise ValueError(f"Required GDC MAF fields are missing: {path}")
            yield from reader


def first_protein_position(hgvsp: str, source_position: str) -> int | None:
    """Return the first affected amino-acid position from accepted annotations."""

    match = re.search(r"\d+", hgvsp)
    if match is None:
        match = re.match(r"\d+", source_position)
    return int(match.group()) if match else None


def aggregate_mutations(
    rows: Iterable[dict[str, str]], parameters: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Select and aggregate recurrent canonical PIK3CA protein changes."""

    gene = str(parameters["gene"])
    transcript = str(parameters["canonicalTranscript"])
    protein_length = int(parameters["proteinLength"])
    classes = {str(value) for value in parameters["proteinAlteringClasses"]}
    barcode_length = int(parameters["tcgaSampleBarcodeLength"])
    threshold = int(parameters["minimumDistinctSampleCount"])
    samples: dict[tuple[int, str, str], set[str]] = defaultdict(set)
    source_positions: dict[tuple[int, str, str], set[str]] = defaultdict(set)
    counts: dict[str, int] = defaultdict(
        int,
        {
            "noncanonicalTranscriptRows": 0,
            "nonProteinAlteringRows": 0,
            "unplottableRows": 0,
        },
    )

    for row in rows:
        counts["mafRows"] += 1
        if row["NCBI_Build"] != "GRCh38":
            raise ValueError("Accepted GDC MAF rows must use GRCh38.")
        if row["Hugo_Symbol"] != gene:
            continue
        counts["pik3caRows"] += 1
        if row["Transcript_ID"].split(".", 1)[0] != transcript:
            counts["noncanonicalTranscriptRows"] += 1
            continue
        variant_class = row["Variant_Classification"]
        if variant_class not in classes:
            counts["nonProteinAlteringRows"] += 1
            continue

        hgvsp = row["HGVSp_Short"]
        position = first_protein_position(hgvsp, row["Protein_position"])
        if position is None or not hgvsp.startswith("p."):
            counts["unplottableRows"] += 1
            continue
        if not 1 <= position <= protein_length:
            raise ValueError(f"Protein position is outside P42336: {position}")
        barcode = row["Tumor_Sample_Barcode"]
        if len(barcode) < barcode_length or not barcode.startswith("TCGA-"):
            raise ValueError(f"Invalid TCGA tumour barcode: {barcode}")

        mutation = hgvsp.removeprefix("p.")
        key = position, mutation, variant_class
        samples[key].add(barcode[:barcode_length])
        source_positions[key].add(row["Protein_position"])
        counts["plottableRows"] += 1

    all_rows: list[dict[str, Any]] = []
    result: list[dict[str, Any]] = []
    for position, mutation, variant_class in sorted(samples):
        sample_count = len(samples[(position, mutation, variant_class)])
        output_row: dict[str, Any] = {
            "position": position,
            "mutation": mutation,
            "sampleCount": sample_count,
            "variantClass": variant_class,
            "sourceProteinPosition": ";".join(
                sorted(source_positions[(position, mutation, variant_class)])
            ),
        }
        all_rows.append(output_row)
        if sample_count >= threshold:
            result.append(output_row)
    counts["uniqueMutations"] = len(all_rows)
    counts["plottedMutations"] = len(result)
    counts["omittedBelowThresholdMutations"] = len(all_rows) - len(result)
    counts["distinctMutatedSamples"] = len(
        {sample for sample_set in samples.values() for sample in sample_set}
    )
    return result, dict(counts)


def select_domains(
    path: Path, source: dict[str, Any], parameters: dict[str, Any]
) -> list[dict[str, Any]]:
    """Select the accepted P42336 domain annotations."""

    record: Any = json.loads(path.read_text(encoding="utf-8"))
    audit = record["entryAudit"]
    sequence = record["sequence"]
    expected = (
        record["primaryAccession"] == source["accession"],
        audit["entryVersion"] == source["entryVersion"],
        audit["sequenceVersion"] == source["sequenceVersion"],
        sequence["length"] == source["sequenceLength"],
        sequence["md5"] == source["sequenceMd5"],
    )
    if not all(expected):
        raise ValueError("UniProt identity does not match provenance.")

    labels = parameters["domainLabels"]
    domains = [
        {
            "start": feature["location"]["start"]["value"],
            "end": feature["location"]["end"]["value"],
            "label": labels[feature["description"]],
            "description": feature["description"],
        }
        for feature in record["features"]
        if feature["type"] == "Domain" and feature["description"] in labels
    ]
    domains.sort(key=lambda row: int(row["start"]))
    protein_length = int(parameters["proteinLength"])
    if len(domains) != len(labels) or any(
        not 1 <= int(row["start"]) <= int(row["end"]) <= protein_length
        for row in domains
    ):
        raise ValueError("Accepted P42336 domains are incomplete or invalid.")
    return domains


def write_tsv(
    rows: list[dict[str, Any]], fields: tuple[str, ...], destination: Path
) -> None:
    """Write a deterministic tab-delimited table."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    try:
        with temporary.open("w", encoding="utf-8", newline="") as output_file:
            writer = csv.DictWriter(
                output_file,
                fieldnames=fields,
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def verify_outputs(provenance: dict[str, Any]) -> None:
    """Verify accepted output fingerprints and row counts."""

    for value in provenance["outputs"].values():
        path = RECIPE_DIR / value["path"]
        validate_file(path, int(value["fileSizeBytes"]), "sha256", value["sha256"])
        with path.open(encoding="utf-8", newline="") as input_file:
            record_count = sum(1 for _ in csv.DictReader(input_file, delimiter="\t"))
        if record_count != int(value["recordCount"]):
            raise ValueError(f"Output record count does not match provenance: {path}")


def validate_accepted_run(
    mutations: list[dict[str, Any]],
    domains: list[dict[str, Any]],
    counts: dict[str, int],
    provenance: dict[str, Any],
) -> None:
    """Require accepted counts, domains, and hotspot values."""

    validation = provenance["validation"]
    if counts != validation["mutationAggregation"]:
        raise ValueError(
            "Mutation aggregation counts do not match provenance: "
            + json.dumps(
                {
                    "observed": counts,
                    "expected": validation["mutationAggregation"],
                }
            )
        )
    if len(domains) != validation["domains"]["featureCount"]:
        raise ValueError("Domain count does not match provenance.")
    observed = {row["mutation"]: row["sampleCount"] for row in mutations}
    if any(
        observed.get(name) != count for name, count in validation["hotspots"].items()
    ):
        raise ValueError("Expected PIK3CA hotspot counts do not match provenance.")


def main() -> None:
    """Prepare or verify the accepted recipe outputs."""

    args = parse_args()
    provenance = load_provenance()
    if args.verify_only:
        verify_outputs(provenance)
        print("Accepted outputs verified.")
        return

    gdc_source = source_by_id(provenance, "gdc-tcga-brca-open-masked-somatic-mafs")
    uniprot_source = source_by_id(provenance, "uniprot-p42336-entry-version-243")
    locks = gdc_files(gdc_source)
    maf_paths = resolve_gdc_inputs(args.maf_directory, gdc_source, locks)
    uniprot_path = resolve_uniprot(args.uniprot, uniprot_source)
    mutations, counts = aggregate_mutations(
        maf_rows(maf_paths), provenance["parameters"]
    )
    domains = select_domains(uniprot_path, uniprot_source, provenance["parameters"])
    validate_accepted_run(mutations, domains, counts, provenance)
    write_tsv(mutations, MUTATION_FIELDS, OUTPUT_DIR / "mutations.tsv")
    write_tsv(domains, DOMAIN_FIELDS, OUTPUT_DIR / "domains.tsv")
    verify_outputs(provenance)
    print("Prepared and verified accepted outputs.")


if __name__ == "__main__":
    main()
