# HEK293T RNF7 direct-RNA coverage and m6A

This recipe prepares a compact transcript-coordinate view of ONT direct-RNA
sequencing reads from matched HEK293T wild-type and METTL3-knockout samples.
It combines published RNF7 alignments from the xPore demo, GRCh38 transcript
sequence reconstructed from Ensembl exon responses, and already-computed m6Anet
site probabilities from Hendra et al.

## Why this dataset

RNF7 transcript ENST00000273480.3 is one of three genes in the official xPore
demo. Its first 920 nucleotides contain 77 wild-type and 151 knockout demo
alignments and twelve candidate DRACH sites. One site at transcript position
614 has a pronounced probability difference (0.989 in wild type and 0.304 in
the knockout), making the small extract useful for connecting aggregate
coverage, site-level modification evidence, transcript structure, and the
individual long reads underneath.

The alignments are a teaching subset, not a quantitative replicate comparison.
The coverage shapes therefore describe only the reads included in the xPore
demo archive.

## Run

Python 3.12 or newer and `uv` are required:

```bash
uv run --locked --script \
  recipes/xpore-hek293t-rnf7-m6a/scripts/prepare.py
```

The script downloads and verifies the pinned xPore demo archive and m6Anet
Supplementary Table 6, extracts only the two indexed BAMs and demo GTF, and
prepares the RNF7 tables. Pass `--verify-only` to validate an existing output.

## Outputs

- `output/rnf7-direct-rna.json.gz` contains named `coverage`, `reads`, `events`,
  `sequence`, `sites`, and `exons` tables plus display metadata. Alignment-event
  rows identify mismatches, insertions, deletions, skipped regions, and
  soft-clipped ends derived from each read's sequence and CIGAR operations.
- `specs/rnf7-direct-rna.json` is a local GenomeSpy prototype with overlaid WT
  and knockout coverage bars, compact condition-level m6Anet markers on the
  reference sequence, read-level alignment events, separate condition pileups,
  and overview brushing. It loads the ignored output with a relative
  `../output/...` URL.

All displayed coordinates are zero-based transcript coordinates on
ENST00000273480.3. Coverage is recorded both as aligned-read count and as the
fraction of the condition's retained primary reads covering each nucleotide.
Read identifiers are replaced with stable condition-local labels.

## Validation and limitations

The preparation verifies both source files, the five selected archive members,
the BAM indexes and reference length, the RNF7 transcript/exon contract, read
counts, coordinate bounds, coverage/count consistency, twelve site identities,
and the prominent position-614 WT/KO contrast. Exact accepted-run identities
and summaries are in `provenance.json`.

The demo BAMs are transcript-aligned and deliberately small. They do not show
genomic introns, and their read counts must not be interpreted as expression or
differential-coverage estimates. Alignment events show disagreement with the
reference, not RNA modifications. m6Anet probabilities are model scores, not
direct biochemical measurements or per-read calls in this output. They are
published condition-level scores and were not recomputed from the selected demo
alignments.

## Data rights

The [rights review](RIGHTS.md) finds the derived extract eligible for
GenomeSpy-managed hosting under CC BY 4.0 with attribution and a modification
notice. The proposed release root is recorded in `provenance.json`.
