# TCGA-BRCA GDC PIK3CA mutations

This recipe aggregates recurrent protein-altering `PIK3CA` mutations from the
open GDC TCGA-BRCA masked somatic MAF collection and pairs them with the five
main domains of reviewed human UniProt entry P42336.

## Why this dataset

The accepted GDC source selection is the exact 992-file TCGA-BRCA collection
returned for open `Masked Somatic Mutation` files from the `Aliquot Ensemble
Somatic Variant Merging and Masking` workflow. The input MAFs use GRCh38, but
the output deliberately discards genomic loci and plots mutations on the
1,068-residue canonical PIK3CA protein. The accepted transcript is
`ENST00000263967`, matching the P42336 canonical protein used for its domain
annotations.

PIK3CA has several recurrent breast-cancer hotspots and multiple well-known
protein domains. The compact result is useful for demonstrating a GenomeSpy
lollipop plot: height encodes distinct tumour-sample count, colour separates
variant classes, and a linked protein track supplies structural context. The
recipe-local spec preserves those maintained-example semantics without
embedding processed patient-derived rows in the spec.

## Run

Python 3.12 or newer is required. The ordinary command downloads any missing
pinned GDC files and the accepted UniProt record, verifies every input, and
writes both outputs:

```bash
uv run --script recipes/tcga-brca-gdc-pik3ca-mutations/scripts/prepare.py
```

Existing source files can be reused without copying them. The MAF directory
must contain `<GDC file UUID>/<filename>` paths:

```bash
uv run --script recipes/tcga-brca-gdc-pik3ca-mutations/scripts/prepare.py \
  --maf-directory /path/to/mafs \
  --uniprot /path/to/uniprot-P42336.json
```

Use `--verify-only` to check existing outputs against `provenance.json`.
Source discovery is intentionally outside the normal preparation command:
changing the GDC query result requires reviewing and replacing the compact
accepted file list in `provenance.json`, then accepting new output fingerprints.

The transformation keeps protein-altering rows on transcript
`ENST00000263967`, takes the first affected residue from `HGVSp_Short`, and
falls back to the first GDC `Protein_position` residue only when necessary.
Counts are over distinct 16-character TCGA tumour-sample barcodes for the same
position, protein change, and variant class. Events seen in fewer than two
samples are omitted from the accepted visualization output.

## Outputs

- `output/mutations.tsv` contains `position`, `mutation`, `sampleCount`,
  `variantClass`, and `sourceProteinPosition`. `position` is a one-based
  amino-acid coordinate on P42336 sequence version 2, not a genomic coordinate.
- `output/domains.tsv` contains `start`, `end`, `label`, and `description` for
  the five selected P42336 domains. Protein intervals are one-based and closed.
- [`specs/overview.json`](specs/overview.json) loads both tables through
  relative `../output/...` URLs.

## Validation and limitations

The accepted run verifies all 992 GDC UUID, filename, size, and MD5 locks plus
the UniProt JSON SHA-256, accession, entry and sequence versions, sequence
length, and sequence MD5. It reads 89,568 MAF rows, finds 379 `PIK3CA` rows,
retains 369 plottable protein-altering rows, and emits 26 recurrent events from
66 unique protein changes. Exact counts and output fingerprints are recorded
in `provenance.json`.

The GDC somatic MAFs are intentionally conservative: potentially identifying
germline calls and some true somatic calls are masked or removed upstream. The
two-sample cutoff is a display choice, not a significance threshold. A tumour
sample can contribute to multiple mutations, and no clinical or outcome
interpretation is supported. The accepted GDC selection is a snapshot; a new
discovery query may return a different collection. The mutable UniProt REST URL
may also advance beyond accepted entry version 243, in which case the checksum
will fail and a reviewed provenance update is required.

## Data rights

The [rights review](RIGHTS.md) finds both transformed tables eligible for
GenomeSpy-managed hosting with TCGA acknowledgment and UniProt CC BY 4.0
attribution and change marking.

Proposed release root:
`https://data.genomespy.app/datasets/tcga-brca-gdc-pik3ca-mutations/v1/`.
