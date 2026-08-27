# NIST HG002 GRCh38 BAM slice

This recipe extracts and downsamples a 200 kb region from the NIST Genome in a
Bottle (GIAB) HG002 300x whole-genome BAM. The result is a coordinate-sorted,
indexed BAM/BAI pair for a GenomeSpy read-alignment example.

## Why this dataset

HG002 / NA24385 is a stable and well-documented benchmark sample. The selected
`chr20:9,950,000-10,100,000` region is small enough for an example while
retaining realistic paired reads, mismatches, indels, soft clipping, mapping
qualities, and base qualities.

The pair demonstrates lazy BAM loading, HTTP range requests, and adjacent BAI
discovery without synthetic alignments. Approximately 99x mean depth preserves
enough feature support for pileup and filtering views while keeping the BAM near
10 MB.

## Run

The recipe requires `samtools` 1.23.1 and network access:

```bash
uv run --script recipes/nist-hg002-grch38-bam-slice/scripts/prepare.py
```

It verifies the pinned GIAB index and parent BAI, retains 33% of templates with
seed 42, and creates the output pair. Use `--verify-only` to check existing
outputs against accepted provenance.

## Outputs

- `output/alignments.bam` — coordinate-sorted alignment slice;
- `output/alignments.bam.bai` — index required for lazy loading.

The samtools region expression is one-based and inclusive. Reads overlapping
the region may start outside it. [`specs/overview.json`](specs/overview.json)
loads the BAM using `../output/alignments.bam`.

## Validation and limitations

The accepted output passes `samtools quickcheck` and indexed queries and has
101,867 primary records. It contains real insertions, deletions, soft clips,
mismatches, and paired-read variation; exact counts and checksums are in
`provenance.json`.

This reduced visualization extract is not suitable for clinical interpretation,
variant calling, benchmarking, genealogy, or re-identification.

## Data rights

The [rights review](RIGHTS.md) permits hosting the reduced pair with GIAB/NIST
attribution and the non-clinical limitation.

Proposed release root:
`https://data.genomespy.app/datasets/nist-hg002-grch38-bam-slice/v1/`, containing
`alignments.bam` and `alignments.bam.bai`.
