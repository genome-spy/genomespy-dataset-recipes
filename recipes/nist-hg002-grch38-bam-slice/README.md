# NIST HG002 GRCh38 BAM slice

This recipe prepares a downsampled 200 kb alignment slice from the NIST Genome
in a Bottle (GIAB) HG002 300x whole-genome BAM. The local GenomeSpy spec shows
coverage, mismatches, insertions, CIGAR operations, mapping quality, base
quality, and read direction from a real coordinate-sorted BAM/BAI pair.

The recipe is `ready`. The retained output pair and visualization have been
validated. The outputs are eligible for GenomeSpy-managed hosting, but this
recipe has not uploaded them.

## Why this source

- Sample: HG002 / NA24385 from the GIAB Ashkenazi Jewish trio
- Source: NIST/NHGRI 300x Illumina whole-genome alignment
- Aligner: Novoalign
- Assembly: GRCh38
- Region: `chr20:9,950,000-10,100,000`

GIAB provides a stable, well-documented benchmark sample with public source
indexes and checksum records. The selected slice is small enough for an example
while retaining realistic paired-read structure and alignment annotations.

## Why it works as a GenomeSpy example

The data exercise lazy BAM loading and BAI companion discovery through HTTP
range requests. Around the initial locus `chr20:10,031,817-10,031,936`, the
reads contain mismatches, insertions, deletions, soft clipping, mapping-quality
variation, and base-quality values. This supports an IGV-like multitrack
example without synthetic records.

The slice has approximately 99x mean depth. That is denser than a minimal demo,
but it deliberately preserves enough feature support for filtering and pileup
views while remaining about 10 MB.

## Preparation

The ordinary run requires `samtools` 1.23.1 and network access. From the
repository root:

```bash
uv run --locked --script \
  recipes/nist-hg002-grch38-bam-slice/scripts/prepare.py
```

The script verifies the pinned GIAB index and parent BAI, extracts the region
with `samtools view`, retains 33% of templates using seed 42, writes
`output/alignments.bam`, and creates `output/alignments.bam.bai`. The full
300x BAM is read remotely through its index rather than downloaded.

To validate already prepared outputs against accepted provenance:

```bash
uv run --locked --script \
  recipes/nist-hg002-grch38-bam-slice/scripts/prepare.py --verify-only
```

The committed checksums reproduce with the accepted samtools 1.23.1 workflow.
BAM compression can vary between samtools releases, so a tool-version change
requires review of the documented semantic checks before provenance is updated.

## Outputs and coordinates

| File | Purpose |
| --- | --- |
| `output/alignments.bam` | Coordinate-sorted, region-extracted, downsampled alignments |
| `output/alignments.bam.bai` | BAM index required by GenomeSpy lazy loading |

SAM/BAM alignment positions are one-based in SAM text and represented according
to the BAM specification internally. The samtools region expression is
one-based and inclusive. Reads overlapping the requested region may begin
outside its bounds.

## Validation

The accepted pair passes `samtools quickcheck` and indexed region queries. It
contains 101,867 primary records: 101,159 mapped, 100,116 properly paired, and
709 singletons. No secondary, supplementary, or duplicate records are present.
The records include 2,343 insertions, 2,066 deletions, 3,892 soft clips, and
28,849 records with a nonzero `NM` tag. Both `MD` and `NM` are present on
101,159 records.

This is a selected, downsampled visualization extract. It is not suitable for
clinical interpretation, variant calling, benchmarking, genealogy, or
re-identification.

## Local visualization

Start the GenomeSpy development server from a sibling GenomeSpy checkout and
open:

```text
http://localhost:8080/?spec=private/genomespy-dataset-recipes/recipes/nist-hg002-grch38-bam-slice/specs/overview.json
```

The spec loads `../output/alignments.bam`; GenomeSpy resolves the adjacent BAI.

## Data rights

The accepted [data-rights review](RIGHTS.md) records NIST's statement that the
GIAB trio was consented for commercial redistribution and concludes that this
reduced derived pair is eligible for GenomeSpy-managed hosting. A hosted release
must retain GIAB/NIST attribution, citations, and the non-clinical limitation.

Repository CC0 covers this README, the authored preparation script, and the
local GenomeSpy spec. It does not cover the BAM, BAI, or upstream data.
