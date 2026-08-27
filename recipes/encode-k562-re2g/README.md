# ENCODE K562 regulatory element–gene links

This recipe prepares released ENCODE-rE2G predictions for untreated K562 cells.
The local GenomeSpy prototype shows candidate regulatory element intervals,
predicted element-to-gene links, and target-gene transcription start sites
(TSSs). These are K562-context model predictions, not definitive or universal
regulatory relationships.

The recipe is `ready`. Its released ENCODE source, generated outputs, and local
visualization have been validated. The outputs are eligible for
GenomeSpy-managed hosting under the accepted data-rights review, but they have
not yet been published through this recipe.

## Why this source

- ENCODE annotation:
  [ENCSR627ANP](https://www.encodeproject.org/annotations/ENCSR627ANP/)
- Pinned released file:
  [ENCFF976OKL](https://www.encodeproject.org/files/ENCFF976OKL/)
- Biosample: untreated K562 human chronic-myeloid-leukemia cell line
- Assembly: GRCh38
- Experimental DNase-seq input: ENCSR000EOT
- Software recorded by ENCODE: ENCODE-rE2G 1.0.0 with ABC 1.1.2

The annotation contains two released GRCh38 files with the output type
`thresholded element gene links`. The pinned product is explicitly identified
as `encode_re2g_predictions` in its ENCODE alias and submitted filename. This
avoids silently selecting the separate ABC-only product.

## Why it works as a GenomeSpy example

The source naturally combines genomic intervals, long-range links, quantitative
model scores, and gene endpoints. It demonstrates coordinated genomic tracks
and link marks without requiring a large lazy-loading format.

The initial domain `chr7:106,800,000-107,300,000` is centered on `PRKAR2B`. It
is less crowded than the tested MYC window while still showing 52 crossing
links, 36 candidate elements, seven unique target-gene endpoints, and link
distances from 33 bp to 1,044,314 bp. The target-gene TSSs for `HBP1`, `PIK3CG`,
and `PRKAR2B` lie inside the domain.

## Preparation

From the repository root:

```bash
uv run --locked --script recipes/encode-k562-re2g/scripts/prepare.py
```

The ordinary run reads `sources.lock.json`. It downloads the exact pinned source
to ignored `download/` when missing, verifies MD5 and SHA-256, and refuses a
different file. To reproduce from an existing source without copying it first:

```bash
uv run --locked --script recipes/encode-k562-re2g/scripts/prepare.py \
  --source /path/to/ENCFF976OKL.bed.gz
```

Source refresh is intentionally manual: resolve current ENCODE metadata, review
the selected accession and terms, then update `sources.lock.json` in the same
change as a newly accepted run. An ordinary run never discovers a new source.

The script writes three deterministic gzip-compressed TSV files under ignored
`output/`:

| File | Records | Purpose |
| --- | ---: | --- |
| `regulatory-element-gene-links.tsv.gz` | 87,489 | One row per thresholded interaction |
| `candidate-regulatory-elements.tsv.gz` | 58,828 | Unique element intervals |
| `target-gene-tss.tsv.gz` | 14,465 | Unique target-gene/TSS endpoints |

Gzip-compressed eager TSV keeps the workflow and spec simple. The complete
interaction relation is about 2.8 MB compressed; bgzip and Tabix would not add a
material loading benefit.

## Coordinates and fields

Element intervals retain BED's zero-based, half-open convention. `TargetGeneTSS`
is retained as a zero-based genomic point/boundary coordinate. `elementMid` is
`(elementStart + elementEnd) / 2`; 17,192 half-base midpoints remain exact.

The interaction output contains:

```text
chrom elementStart elementEnd elementMid elementId elementClass geneTss
geneId geneSymbol distanceToTss re2gScore abcScore
```

Element classes `promoter`, `genic`, and `intergenic` are source model classes,
not ENCODE Registry PLS/pELS/dELS classes. Coordinate-derived element IDs are
not presented as Registry cCRE accessions.

## Validation

The preparation run validates:

- exact source checksums and required BED3+ columns;
- GRCh38 primary chromosome bounds and positive-width intervals;
- finite scores within `[0, 1]`;
- exact equality of source distance and
  `abs(TargetGeneTSS - elementMid)`, including half-base midpoints;
- populated Ensembl-style gene IDs and symbols;
- deterministic sorting and exact-row deduplication;
- expected counts and the informative initial locus.

No exact duplicate interactions were found. Nine Ensembl IDs have conflicting
symbol, TSS, or chromosome annotations in the released source. The recipe
preserves and records these anomalies rather than guessing corrections.

To verify existing outputs against accepted provenance without reading the
source:

```bash
uv run --locked --script recipes/encode-k562-re2g/scripts/prepare.py --verify-only
```

## Local visualization

Start the GenomeSpy development server from the sibling GenomeSpy repository
with `npm start`, then open:

```text
http://localhost:8080/?spec=private/genomespy-dataset-recipes/recipes/encode-k562-re2g/specs/overview.json
```

The spec loads all three outputs through relative `../output/...` URLs.

## Data rights

The accepted [data-rights review](RIGHTS.md) concludes that ENCODE's
unrestricted-use policy permits GenomeSpy to host these transformed outputs.
Hosted files must credit the ENCODE Consortium and the Jesse Engreitz lab at
Stanford, identify ENCSR627ANP and ENCFF976OKL, and link to the authoritative
source and policy. Eligibility does not mean the outputs have already been
uploaded.

Repository CC0 covers this README, the authored preparation script, and the
local GenomeSpy spec. It does not cover the ENCODE source or any generated TSV.
