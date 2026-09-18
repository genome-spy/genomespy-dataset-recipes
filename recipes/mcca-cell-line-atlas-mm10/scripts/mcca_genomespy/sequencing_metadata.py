# mypy: ignore-errors
"""Create sequencing availability metadata from ENA run reports.

The MCCA processed copy-ratio table does not say which assay produced each
displayed profile. ENA run reports still expose sample-level raw data
availability through `sample_alias` values such as `MCCA0506-Cells-lcWGS`.
This module parses those aliases and writes a small metadata table that tells
GenomeSpy whether each MCCA cell line has lcWGS runs, WES runs, or both.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

LCWGS_RUN_REPORT = "ena_lcwgs_runs.tsv"
WES_RUN_REPORT = "ena_wes_runs.tsv"
MCCA_ID_PATTERN = re.compile(r"MCCA\d{4}")
SEQUENCING_METADATA_SCHEMA = {
    "MCCA-ID": pa.string(),
    "SequencingAvailability": pa.string(),
}


def extract_mcca_id(value: str) -> str:
    match = MCCA_ID_PATTERN.search(value)
    if match is None:
        raise ValueError("Cannot find MCCA ID in ENA sample alias: " + value)
    return match.group(0)


def read_run_report_sample_ids(path: Path) -> set[str]:
    with path.open(newline="") as file:
        return {
            extract_mcca_id(row["sample_alias"])
            for row in csv.DictReader(file, delimiter="\t")
        }


def sequencing_type(has_lcwgs: bool, has_wes: bool) -> str | None:
    if has_lcwgs and has_wes:
        return "lcWGS+WES"
    if has_lcwgs:
        return "lcWGS only"
    if has_wes:
        return "WES only"
    return None


def sequencing_metadata_rows(
    sample_rows: Iterable[dict[str, Any]],
    lcwgs_sample_ids: set[str],
    wes_sample_ids: set[str],
) -> Iterable[dict[str, str | None]]:
    for row in sample_rows:
        sample_id = row["MCCA-ID"]
        yield {
            "MCCA-ID": sample_id,
            "SequencingAvailability": sequencing_type(
                sample_id in lcwgs_sample_ids,
                sample_id in wes_sample_ids,
            ),
        }


def write_sequencing_metadata_parquet(
    path: Path,
    rows: Iterable[dict[str, str | None]],
) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    row_list = list(rows)
    arrays = [
        pa.array(
            [row[column] for row in row_list],
            type=schema_type,
        )
        for column, schema_type in SEQUENCING_METADATA_SCHEMA.items()
    ]
    table = pa.Table.from_arrays(
        arrays,
        names=list(SEQUENCING_METADATA_SCHEMA),
    )
    pq.write_table(table, path, compression="snappy")
    return len(row_list)


def read_sample_ids(path: Path) -> list[str]:
    table = pq.read_table(path, columns=["MCCA-ID"])
    return table.column("MCCA-ID").to_pylist()


def write_sequencing_metadata(
    raw_dir: Path,
    output_path: Path,
    sample_ids: Iterable[str],
) -> int:
    return write_sequencing_metadata_parquet(
        output_path,
        sequencing_metadata_rows(
            ({"MCCA-ID": sample_id} for sample_id in sample_ids),
            read_run_report_sample_ids(raw_dir / LCWGS_RUN_REPORT),
            read_run_report_sample_ids(raw_dir / WES_RUN_REPORT),
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Wrangle ENA run reports into MCCA sequencing metadata."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "download",
        help="Directory containing downloaded ENA run reports.",
    )
    parser.add_argument(
        "--samples-path",
        type=Path,
        default=(
            Path(__file__).resolve().parents[2]
            / "output"
            / "processed"
            / "samples.parquet"
        ),
        help="Generated MCCA sample table that provides the visualization sample IDs.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=(
            Path(__file__).resolve().parents[2]
            / "output"
            / "processed"
            / "sequencing.parquet"
        ),
        help="Output Parquet metadata file.",
    )
    args = parser.parse_args()

    count = write_sequencing_metadata(
        args.raw_dir,
        args.output_path,
        read_sample_ids(args.samples_path),
    )
    print(f"Wrote {count} sequencing metadata rows")


if __name__ == "__main__":
    main()
