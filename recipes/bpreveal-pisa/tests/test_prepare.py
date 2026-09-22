# SPDX-License-Identifier: CC0-1.0
# mypy: ignore_missing_imports=True

from __future__ import annotations

import bz2
import importlib.util
import sys
import tarfile
from pathlib import Path
from types import ModuleType

import h5py
import numpy as np
import pyarrow.parquet as pq
import pytest


def load_prepare() -> ModuleType:
    """Load the recipe entrypoint without requiring a package install."""

    path = Path(__file__).resolve().parents[1] / "scripts" / "prepare.py"
    spec = importlib.util.spec_from_file_location("bpreveal_pisa_prepare", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load prepare.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


prepare = load_prepare()


def reference_shear(raw: np.ndarray) -> np.ndarray:
    """Implement the documented BPReveal shear literally for comparison."""

    values = raw.sum(axis=2, dtype=np.float32)
    rows, receptive_field = values.shape
    sheared = np.zeros((rows, receptive_field + rows), dtype=np.float32)
    for row in range(rows):
        sheared[row, row : row + receptive_field] = values[row]
    return sheared[:, receptive_field // 2 : -receptive_field // 2]


def write_synthetic_h5(path: Path, rows: int, receptive_field: int) -> np.ndarray:
    """Write deterministic PISA-shaped values and return them."""

    raw = np.zeros((rows, receptive_field, 4), dtype=np.float32)
    for row in range(rows):
        for column in range(receptive_field):
            raw[row, column, 0] = row * 100 + column
    with h5py.File(path, "w") as output:
        output.create_dataset("shap", data=raw)
    return raw


def test_direct_slice_matches_even_receptive_field(tmp_path: Path) -> None:
    path = tmp_path / "even.h5"
    raw = write_synthetic_h5(path, rows=7, receptive_field=4)
    expected = reference_shear(raw)
    observed = prepare.read_sheared_slice(path, 1, 6, 2, 7)
    np.testing.assert_array_equal(observed, expected[1:6, 2:7])


def test_direct_slice_matches_odd_receptive_field(tmp_path: Path) -> None:
    path = tmp_path / "odd.h5"
    raw = write_synthetic_h5(path, rows=7, receptive_field=5)
    expected = reference_shear(raw)
    observed = prepare.read_sheared_slice(path, 0, 7, 0, 7)
    np.testing.assert_array_equal(observed, expected)


def test_combined_slice_sums_files(tmp_path: Path) -> None:
    first = tmp_path / "first.h5"
    second = tmp_path / "second.h5"
    raw = write_synthetic_h5(first, rows=7, receptive_field=5)
    with h5py.File(second, "w") as output:
        output.create_dataset("shap", data=raw * 2)
    observed = prepare.read_combined_slice(
        {"first": first, "second": second},
        ("first", "second"),
        1,
        6,
        1,
        6,
    )
    expected = reference_shear(raw)[1:6, 1:6] * 3
    np.testing.assert_array_equal(observed, expected)


def test_matrix_parquet_contract(tmp_path: Path) -> None:
    panel = prepare.Panel(
        identifier="test",
        assembly="test",
        chrom="chr1",
        genome_window_start=100,
        midpoint_offset=2,
        input_width=3,
        output_width=5,
        pisa_members=("unused",),
        tracks=(),
        motifs_member="unused",
        threshold=None,
        color_span=1,
    )
    values = np.arange(15, dtype=np.float32).reshape(5, 3)
    path = tmp_path / "matrix.parquet"
    assert prepare.write_matrix(path, panel, values) == 15
    table = pq.read_table(path)
    assert table.schema == prepare.MATRIX_SCHEMA
    assert table.column("input").to_pylist()[:3] == [101, 102, 103]
    assert table.column("output").to_pylist()[:4] == [100, 100, 100, 101]
    np.testing.assert_allclose(
        table.column("effect").to_numpy(), values.reshape(-1) * prepare.LOG2_E
    )


def test_link_threshold_and_draw_order(tmp_path: Path) -> None:
    panel = prepare.Panel(
        identifier="test",
        assembly="test",
        chrom="chr1",
        genome_window_start=100,
        midpoint_offset=2,
        input_width=3,
        output_width=5,
        pisa_members=("unused",),
        tracks=(),
        motifs_member="unused",
        threshold=0.5,
        color_span=1,
    )
    values = np.array(
        [[0.0, 0.5, -0.7], [0.2, -1.0, 0.0], [0.0, 0.0, 0.0]],
        dtype=np.float32,
    )
    path = tmp_path / "links.parquet"
    assert prepare.write_links(path, panel, values) == 3
    table = pq.read_table(path)
    assert table.schema == prepare.LINK_SCHEMA
    magnitudes = np.abs(table.column("effect").to_numpy())
    assert np.all(magnitudes[:-1] <= magnitudes[1:])


def test_archive_member_matching_allows_a_prefix() -> None:
    member = prepare.MEMBERS[0]
    assert prepare.member_for_archive_path(member.suffix) == member
    assert prepare.member_for_archive_path("deposit/" + member.suffix) == member
    assert prepare.member_for_archive_path("unrelated/file.txt") is None


def test_member_selection_count_matches_provenance() -> None:
    assert len(prepare.MEMBERS) == 4
    assert len({member.identifier for member in prepare.MEMBERS}) == 4
    assert len({member.local_name for member in prepare.MEMBERS}) == 4
    assert all(not Path(member.suffix).is_absolute() for member in prepare.MEMBERS)


def test_fig2cd_panel_selection_is_self_contained() -> None:
    panels = prepare.select_panels("fig2cd-atac")
    assert [panel.identifier for panel in panels] == ["fig2cd-atac"]
    assert {member.identifier for member in prepare.members_for_panels(panels)} == {
        "fig2cdPisa",
        "fig2cdPrediction",
        "fig2cdImportance",
        "fig2cdMotifs",
    }
    assert set(prepare.expected_outputs(panels)) == {
        "fig2c-atac-links.parquet",
        "fig2cd-atac-tracks.parquet",
        "fig2cd-atac-motifs.parquet",
        "fig2d-atac-matrix.parquet",
    }


def test_accepted_output_identity_contract() -> None:
    identities = {
        "example.parquet": {
            "fileSizeBytes": 12,
            "recordCount": 3,
            "sha256": "abc",
            "fields": ["position", "value"],
        },
        "panels.json": {"fileSizeBytes": 34, "sha256": "def"},
    }
    provenance = {
        "outputs": {
            "example": {
                "path": "output/example.parquet",
                "format": "parquet",
                **identities["example.parquet"],
            },
            "panels": {
                "path": "output/panels.json",
                "format": "json",
                **identities["panels.json"],
            },
        }
    }

    prepare.validate_accepted_output_identities(identities, provenance)

    changed = {name: dict(value) for name, value in identities.items()}
    changed["example.parquet"]["sha256"] = "changed"
    with pytest.raises(ValueError, match="sha256 mismatch"):
        prepare.validate_accepted_output_identities(changed, provenance)


def test_concatenated_bzip2_streams_are_supported(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("test\n", encoding="utf-8")
    uncompressed = tmp_path / "test.tar"
    with tarfile.open(uncompressed, "w") as output:
        output.add(source, arcname="prefix/source.txt")
    tar_bytes = uncompressed.read_bytes()
    midpoint = len(tar_bytes) // 2
    archive = tmp_path / "test.tar.bz2"
    archive.write_bytes(
        bz2.compress(tar_bytes[:midpoint]) + bz2.compress(tar_bytes[midpoint:])
    )
    with tarfile.open(archive, "r:bz2") as input_archive:
        assert next(iter(input_archive)).name == "prefix/source.txt"

    index = tmp_path / "archive-members.txt"
    assert prepare.write_archive_index(archive, index, "test-md5") == 1
    assert index.read_text(encoding="utf-8").splitlines() == [
        "# archiveMd5=test-md5",
        "prefix/source.txt",
    ]
    assert prepare.write_archive_index(archive, index, "test-md5") == 1
