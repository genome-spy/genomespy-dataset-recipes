# ENCODE K562 regulatory element–gene links

This recipe converts released ENCODE-rE2G predictions for untreated K562 cells
into three GenomeSpy-ready tables: regulatory element–gene links, candidate
elements, and target-gene transcription start sites. The predictions are
cell-context-specific model results, not definitive regulatory relationships.

## Why this dataset

The pinned source is ENCODE annotation
[ENCSR627ANP](https://www.encodeproject.org/annotations/ENCSR627ANP/), file
[ENCFF976OKL](https://www.encodeproject.org/files/ENCFF976OKL/), on GRCh38. It
is explicitly the ENCODE-rE2G product rather than the separate ABC-only file.

Intervals, quantitative scores, long-range links, and gene endpoints make the
dataset a compact example of coordinated genomic tracks and link marks. The
initial `chr7:106,800,000-107,300,000` view around `PRKAR2B` has 52 links,
36 elements, and seven target genes without being visually overwhelming.

## Run

The standard-library-only Python script downloads and verifies the pinned input
when needed:

```bash
uv run --script recipes/encode-k562-re2g/scripts/prepare.py
```

Use `--source <path>` for an already downloaded copy or `--verify-only` to
check existing outputs against accepted provenance.

## Outputs

| File | Rows | Content |
| --- | ---: | --- |
| `output/regulatory-element-gene-links.tsv.gz` | 87,489 | Thresholded interactions |
| `output/candidate-regulatory-elements.tsv.gz` | 58,828 | Unique element intervals |
| `output/target-gene-tss.tsv.gz` | 14,465 | Unique gene/TSS endpoints |

Element intervals are zero-based and half-open. `geneTss` is a zero-based point
or boundary, and `elementMid` may be a half-base value. Element classes are
source model classes, not ENCODE Registry cCRE classes.

[`specs/overview.json`](specs/overview.json) loads all three files through
relative `../output/...` URLs.

## Validation and limitations

The recipe verifies source and output checksums, required fields, GRCh38 bounds,
scores, distances, sorting, and the initial locus. Nine Ensembl IDs have
conflicting source annotations; they are preserved and listed in
`provenance.json` rather than guessed away.

## Data rights

The [rights review](RIGHTS.md) permits hosting these transformations with
ENCODE and producing-lab attribution.

Proposed release root:
`https://data.genomespy.app/datasets/encode-k562-re2g/v1/`. Artifact names match
the paths under `output/`.
