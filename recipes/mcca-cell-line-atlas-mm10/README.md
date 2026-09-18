# Mouse Cancer Cell Line Atlas (mm10)

This recipe prepares a complete local GenomeSpy App visualization of the Mouse
Cancer Cell Line Atlas (MCCA). It combines cell-line metadata, engineered model
alleles, segmented copy ratios, somatic variants, sequencing availability, and
gene-wise transcriptome metadata for 590 mouse cancer cell lines.

The visualization is an independent GenomeSpy demonstration. It is not
affiliated with, maintained by, or endorsed by the MCCA publication authors.

## Why this dataset

Mueller et al. describe MCCA as a disease-model resource for studying
tissue-specific cancer evolution. It is a useful GenomeSpy example because it
connects heterogeneous sample metadata with genome-wide copy-ratio and mutation
tracks, while the transcriptome Zarr source demonstrates lazy, searchable
high-dimensional metadata. It also exercises a non-human assembly (`mm10`) and
a guided bookmark tour.

The source publication is:

> Mueller, S. et al. A disease model resource reveals core principles of
> tissue-specific cancer evolution. *Nature* 653, 265 (2026).
> <https://doi.org/10.1038/s41586-026-10187-2>

## Run

Python 3.12 or newer and [uv](https://docs.astral.sh/uv/) are required. The
ordinary command downloads missing inputs, verifies all accepted input
identities, creates every output, and verifies the accepted artifact manifest:

```bash
uv run --locked --script \
  recipes/mcca-cell-line-atlas-mm10/scripts/prepare.py
```

Existing accepted inputs and outputs can be checked without downloading or
rewriting them:

```bash
uv run --locked --script \
  recipes/mcca-cell-line-atlas-mm10/scripts/prepare.py --verify-only
```

The migrated focused test suite runs in the same locked environment:

```bash
uv run --locked --script \
  recipes/mcca-cell-line-atlas-mm10/scripts/prepare.py --test
```

The workflow prepares the data as follows:

- retains only canonical mouse chromosomes `chr1`–`chr19`, `chrX`, and `chrY`;
- preserves MCCA metadata names and typed missing values in Parquet;
- parses inherited or engineered alleles from `MouseModelDetailed`;
- summarizes ENA lcWGS and WES run availability by MCCA identifier;
- maps transcriptome Ensembl identifiers through GENCODE M25, computes a
  population-standard-deviation z-score for each gene across samples, and
  writes a chunked Zarr v3 matrix; and
- builds compressed GENCODE M25 gene models scored by NCBI PubMed citation
  counts for label prioritization.

## Outputs

- `output/processed/samples.parquet`: 590 sample annotation rows and 23 fields.
- `output/processed/model-alleles.parquet`: 590 sample rows and 25 parsed allele
  fields plus `MCCA-ID`.
- `output/processed/sequencing.parquet`: lcWGS/WES availability for all 590
  displayed samples.
- `output/processed/copy-ratios.parquet`: 62,693 canonical mm10 half-open
  copy-ratio segments.
- `output/processed/mutations.parquet`: 130,380 canonical mm10 point variants;
  `pos` retains the source `POS-mm10` coordinate.
- `output/processed/expression.zarr`: a 588-by-14,055 float32 matrix of gene-wise
  expression z-scores with sample, symbol, Ensembl-ID, and gene-type arrays.
- `output/external-data/gencodeGenes-mm10.tsv`: 55,274 compressed canonical
  GENCODE M25 gene annotations using zero-based, half-open intervals.
- `output/external-data/cytobands.tsv.gz`: the unchanged UCSC mm10
  `cytoBandIdeo` table.
- [`specs/spec.json`](specs/spec.json): the root GenomeSpy App spec.
- [`specs/bookmarks.json`](specs/bookmarks.json): the guided tour.
- [`specs/index.html`](specs/index.html): a standalone page that loads the root
  spec; the accompanying SVG assets are under `specs/tour/`.

All recipe-local data URLs point to `../output/`. For a local preview, serve
the recipe directory with an HTTP server that supports byte-range requests;
Zarr metadata loading requires range requests.

## Validation and limitations

The accepted run verifies every source and published object by byte size and
SHA-256, validates Parquet dimensions, and checks the Zarr matrix and identifier
array shapes. The focused tests cover value normalization, chromosome
filtering, model-allele parsing, transcriptome z-scoring and identifiers,
GENCODE compression, downloads, sequencing availability, and spec contracts.

Two MCCA metadata rows have no corresponding transcriptome column, so the
sample table contains 590 rows while the expression matrix contains 588. The
sequencing field reports public raw-data availability in ENA, not which assay
produced a displayed copy-ratio profile. Related cell lines are not necessarily
independent biological samples, and the visualization is not intended for
recurrence estimation or clinical interpretation.

## Data rights

The [rights review](RIGHTS.md) records written permission from corresponding
author Ronald Rad and the separate terms for supporting public resources. The
accepted artifacts are eligible for GenomeSpy-managed hosting under the stated
attribution and non-endorsement conditions.

Proposed release root:
`https://data.genomespy.app/datasets/mcca-cell-line-atlas-mm10/v1/`.
