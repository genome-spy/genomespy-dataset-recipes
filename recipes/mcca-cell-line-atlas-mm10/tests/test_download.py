# ruff: noqa: E501

from mcca_genomespy.download import (
    download_files,
    download_group,
    google_drive_confirm_url,
)


def test_google_drive_confirm_url_extracts_large_file_form():
    html = """
    <form id="download-form" action="https://drive.usercontent.google.com/download" method="get">
      <input type="hidden" name="id" value="file-id">
      <input type="hidden" name="export" value="download">
      <input type="hidden" name="confirm" value="t">
      <input type="hidden" name="uuid" value="uuid-value">
    </form>
    """

    assert (
        google_drive_confirm_url(html)
        == "https://drive.usercontent.google.com/download?id=file-id&export=download&confirm=t&uuid=uuid-value"
    )


def test_download_files_puts_cytobands_under_web_data(tmp_path, monkeypatch):
    calls = []

    def fake_download_file(url, output_path):
        calls.append((url, output_path))
        output_path.write_text("downloaded")

    monkeypatch.setattr("mcca_genomespy.download.download_file", fake_download_file)

    raw_dir = tmp_path / "tmp/raw"
    data_dir = tmp_path / "web/data"

    download_files(raw_dir, data_dir)

    assert (
        "https://hgdownload.soe.ucsc.edu/goldenPath/mm10/database/cytoBandIdeo.txt.gz",
        data_dir / "external-data/cytobands.tsv.gz.download",
    ) in calls
    assert (
        "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_mouse/release_M25/gencode.vM25.annotation.gtf.gz",
        raw_dir / "gencode.vM25.annotation.gtf.gz.download",
    ) in calls
    assert (
        "https://www.ebi.ac.uk/ena/portal/api/filereport?accession=PRJEB105230&result=read_run&fields=run_accession,study_accession,sample_accession,secondary_sample_accession,experiment_accession,sample_alias,sample_title,library_strategy,library_source,instrument_model,fastq_ftp,submitted_ftp&format=tsv&download=true&limit=0",
        raw_dir / "ena_lcwgs_runs.tsv.download",
    ) in calls
    assert (
        "https://www.ebi.ac.uk/ena/portal/api/filereport?accession=PRJEB105231&result=read_run&fields=run_accession,study_accession,sample_accession,secondary_sample_accession,experiment_accession,sample_alias,sample_title,library_strategy,library_source,instrument_model,fastq_ftp,submitted_ftp&format=tsv&download=true&limit=0",
        raw_dir / "ena_wes_runs.tsv.download",
    ) in calls
    assert (
        "https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2ensembl.gz",
        raw_dir / "gene2ensembl.gz.download",
    ) in calls


def test_download_group_preserves_existing_files(tmp_path, monkeypatch):
    calls = []
    existing_path = tmp_path / "existing.txt"
    existing_path.write_text("cached")

    def fake_download_file(url, output_path):
        calls.append((url, output_path))

    monkeypatch.setattr("mcca_genomespy.download.download_file", fake_download_file)

    download_group({"existing.txt": "https://example.org/existing.txt"}, tmp_path)

    assert calls == []
    assert existing_path.read_text() == "cached"


def test_download_group_force_refreshes_existing_files(tmp_path, monkeypatch):
    calls = []
    existing_path = tmp_path / "existing.txt"
    existing_path.write_text("cached")

    def fake_download_file(url, output_path):
        calls.append((url, output_path))
        output_path.write_text("downloaded")

    monkeypatch.setattr("mcca_genomespy.download.download_file", fake_download_file)

    download_group(
        {"existing.txt": "https://example.org/existing.txt"},
        tmp_path,
        force=True,
    )

    assert calls == [
        ("https://example.org/existing.txt", tmp_path / "existing.txt.download")
    ]
    assert existing_path.read_text() == "downloaded"


def test_download_group_refreshes_empty_cached_files(tmp_path, monkeypatch):
    calls = []
    existing_path = tmp_path / "empty.txt"
    existing_path.write_bytes(b"")

    def fake_download_file(url, output_path):
        calls.append((url, output_path))
        output_path.write_text("downloaded")

    monkeypatch.setattr("mcca_genomespy.download.download_file", fake_download_file)

    download_group({"empty.txt": "https://example.org/empty.txt"}, tmp_path)

    assert calls == [("https://example.org/empty.txt", tmp_path / "empty.txt.download")]
    assert existing_path.read_text() == "downloaded"


def test_download_group_keeps_partial_download_from_replacing_cached_file(
    tmp_path,
    monkeypatch,
):
    existing_path = tmp_path / "existing.txt"
    existing_path.write_text("cached")

    def failing_download_file(url, output_path):
        output_path.write_text("partial")
        raise RuntimeError("download failed")

    monkeypatch.setattr(
        "mcca_genomespy.download.download_file",
        failing_download_file,
    )

    try:
        download_group(
            {"existing.txt": "https://example.org/existing.txt"},
            tmp_path,
            force=True,
        )
    except RuntimeError:
        pass

    assert existing_path.read_text() == "cached"
