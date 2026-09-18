# mypy: ignore-errors
"""Download public inputs for the MCCA GenomeSpy demo.

This module fetches the source MCCA workbooks, transcriptome archive, GENCODE
mouse M25 annotation, and NCBI gene-annotation source tables into `download/`
by default. It also downloads external visualization support data, currently
UCSC mm10 cytobands, under `output/`. Existing files are kept by default so
failed runs can be resumed. Google Drive downloads may return an intermediate
confirmation page for large files, so the downloader follows that form when
present.
"""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen, urlretrieve

DOWNLOADS = {
    "mutations.xlsx": "https://docs.google.com/spreadsheets/d/1ecjNMXa4R5VCXDzy0NcgeZ3cTL_bwPYp/export?format=xlsx",
    "copy_number_variation.xlsx": "https://docs.google.com/spreadsheets/d/14ugBHdcuWWF0ZxbWWaWN2MD5H_XT6iwo/export?format=xlsx",
    "cell_line_annotations.xlsx": "https://docs.google.com/spreadsheets/d/1nKtQqXtJobVP_5KJrwntVqtUcid8cKQj/export?format=xlsx&gid=1386275249",
    "MCCA-Transcriptomes-VsdBatchCorrected-2025Q2.zip": "https://drive.google.com/uc?export=download&id=1o-Wo4P31z0ddKHRs-k9SCOMEN8-0EbyY",
    "ena_lcwgs_runs.tsv": "https://www.ebi.ac.uk/ena/portal/api/filereport?accession=PRJEB105230&result=read_run&fields=run_accession,study_accession,sample_accession,secondary_sample_accession,experiment_accession,sample_alias,sample_title,library_strategy,library_source,instrument_model,fastq_ftp,submitted_ftp&format=tsv&download=true&limit=0",
    "ena_wes_runs.tsv": "https://www.ebi.ac.uk/ena/portal/api/filereport?accession=PRJEB105231&result=read_run&fields=run_accession,study_accession,sample_accession,secondary_sample_accession,experiment_accession,sample_alias,sample_title,library_strategy,library_source,instrument_model,fastq_ftp,submitted_ftp&format=tsv&download=true&limit=0",
    "gencode.vM25.annotation.gtf.gz": "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_mouse/release_M25/gencode.vM25.annotation.gtf.gz",
    "gene2ensembl.gz": "https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2ensembl.gz",
    "gene2pubmed.gz": "https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2pubmed.gz",
}

DATA_DOWNLOADS = {
    "external-data/cytobands.tsv.gz": "https://hgdownload.soe.ucsc.edu/goldenPath/mm10/database/cytoBandIdeo.txt.gz",
}


class GoogleDriveDownloadFormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_download_form = False
        self.action = ""
        self.inputs: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag == "form" and attr_map.get("id") == "download-form":
            self.in_download_form = True
            self.action = attr_map["action"]
        elif self.in_download_form and tag == "input" and "name" in attr_map:
            self.inputs.append((attr_map["name"], attr_map.get("value") or ""))

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self.in_download_form = False


def google_drive_confirm_url(html: str) -> str | None:
    parser = GoogleDriveDownloadFormParser()
    parser.feed(html)
    if parser.action:
        return parser.action + "?" + urlencode(parser.inputs)
    return None


def download_file(url: str, output_path: Path) -> None:
    with urlopen(url) as response:
        content_type = response.headers.get_content_type()
        content = response.read()

    if content_type == "text/html":
        confirm_url = google_drive_confirm_url(content.decode("utf-8"))
        if confirm_url is not None:
            urlretrieve(confirm_url, output_path)
            return

    output_path.write_bytes(content)


def download_group(
    downloads: dict[str, str],
    output_dir: Path,
    force: bool = False,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for filename, url in downloads.items():
        output_path = output_dir / filename
        temp_path = output_path.with_name(output_path.name + ".download")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists() and output_path.stat().st_size > 0 and not force:
            print(f"Keeping existing {filename}")
        else:
            print(f"Downloading {filename}")
            try:
                download_file(url, temp_path)
                if temp_path.stat().st_size == 0:
                    raise RuntimeError("Downloaded file is empty: " + filename)
                temp_path.replace(output_path)
            finally:
                temp_path.unlink(missing_ok=True)


def download_files(
    raw_dir: Path,
    data_dir: Path = Path("web/data"),
    force: bool = False,
) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)

    download_group(DOWNLOADS, raw_dir, force=force)
    download_group(DATA_DOWNLOADS, data_dir, force=force)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download public MCCA source workbooks."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "download",
        help="Directory for downloaded source workbooks.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "output",
        help="Directory for downloaded generated visualization data.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Download files even when the target path already exists.",
    )
    args = parser.parse_args()

    download_files(args.raw_dir, args.data_dir, force=args.force)


if __name__ == "__main__":
    main()
