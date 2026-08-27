# DynSeq SPI1 binding QTL

This recipe verifies the two original BigWigs used by the DynSeq SPI1 binding-
QTL vignette. They contain projected DeepSHAP contribution scores for reference
C and alternate G alleles of rs5764238 in GM12878 SPI1 ChIP-seq BPNet
predictions.

## Why this dataset

The source files cover only 2,114 bases around one variant while retaining a
score for every nucleotide. They are therefore a compact demonstration of
GenomeSpy's indexed BigWig access and nucleotide-resolution comparison. The
scores show how the model's sequence contributions change between alleles;
they are model explanations, not measured ChIP-seq signal or causal-effect
estimates.

The maintained GenomeSpy consumer already reads the files directly from the
immutable `dynseq-paper` commit
`febc9180d72e92302d35c549002e0d56c79c536e`. This migration preserves that
direct-source design. It does not retain the staging workflow that rewrote the
files into byte-different compact slices, because no maintained consumer uses
those derivatives.

## Run

Python 3.12 or newer is required. The ordinary command downloads missing files
from the pinned commit directly into the ignored `output/` directory and
validates them:

```bash
uv run --locked --script recipes/dynseq-spi1-bqtl/scripts/prepare.py
```

Existing files can be reused as ignored local evidence:

```bash
uv run --locked --script recipes/dynseq-spi1-bqtl/scripts/prepare.py \
  --source-directory /path/to/pinned-bigwigs
```

Use `--verify-only` to validate existing outputs without reading or downloading
sources.

## Outputs

- `output/chip_imp_ref.bw` is the unchanged reference-allele BigWig.
- `output/chip_imp_alt.bw` is the unchanged alternate-allele BigWig.
- [`specs/overview.json`](specs/overview.json) compares the two local files
  through relative `../output/...` URLs.

Both BigWigs contain contiguous one-base, 0-based half-open intervals across
`chr22:43719872-43721986` on GRCh38/hg38. The vignette sets `POS = 43720929`
for rs5764238 and substitutes G for C in the alternate sequence at that
zero-based position. Exact identities and validation summaries are recorded in
`provenance.json`.

## Validation and limitations

The accepted run verifies each immutable Git blob identity, byte size, MD5,
and SHA-256. It opens each file as BigWig; checks the GRCh38 chromosome header,
the sole non-empty chromosome, interval bounds, contiguity, finiteness, and
score range; and confirms that the two alleles have identical interval
coordinates. Each file has 2,114 unit intervals with no gaps.

The local spec focuses on the paired importance-score tracks. The maintained
deployed example additionally looks up hg38 sequence and renders bases as a
sequence logo; that external FASTA is not duplicated by this recipe. The model
scores are tied to the published preprocessing and trained models, and should
not be generalized beyond this vignette.

## Attribution and data rights

The data are from Nair et al., *The dynseq browser track shows context-specific
features at nucleotide resolution*, Nature Genetics 54, 1581–1583 (2022),
[doi:10.1038/s41588-022-01194-w](https://doi.org/10.1038/s41588-022-01194-w).
The SPI1 vignette builds on Tehranchi et al., *Pooled ChIP-Seq Links Variation
in Transcription Factor Binding to Complex Disease Risk* (2016),
[doi:10.1016/j.cell.2016.03.041](https://doi.org/10.1016/j.cell.2016.03.041).

The [rights review](RIGHTS.md) finds the files covered by the DynSeq Zenodo
dataset's CC BY 4.0 terms. The maintained immutable upstream URLs remain the
preferred distribution location, so no GenomeSpy mirror is proposed.
