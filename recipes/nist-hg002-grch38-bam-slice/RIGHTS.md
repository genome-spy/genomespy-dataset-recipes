# Data-rights review

## Scope

This review covers the NIST GIAB HG002 / NA24385 GRCh38 300x BAM identified in
`sources.lock.json` and the recipe's downsampled `output/alignments.bam` and
`output/alignments.bam.bai` pair.

## Evidence

- The authoritative [NIST Genome in a Bottle project page](https://www.nist.gov/programs-projects/genome-bottle)
  states that the Ashkenazi Jewish and Han Chinese Personal Genome Project
  trios were selected because they were consented for commercial redistribution.
- The immutable GIAB alignment index pinned in `sources.lock.json` identifies
  the exact HG002 parent BAM and BAI and reports their MD5 checksums.
- Zook et al., [Extensive sequencing of seven human genomes to characterize
  benchmark reference materials](https://doi.org/10.1038/sdata.2016.25),
  describes the reference samples, consent, and intended benchmark use.

## Interpretation

The provider's explicit commercial-redistribution statement supports public
redistribution of this much smaller derived alignment slice. The recipe does
not claim that human genomic data are anonymous or risk-free; it preserves the
provider identity and limits the example to visualization.

## Conditions

- Credit NIST Genome in a Bottle and identify HG002 / NA24385.
- Link to the NIST project page, pinned GIAB source index, and cited paper.
- Describe the files as a GenomeSpy-produced downsampled regional extract.
- Preserve the warnings against clinical interpretation, genealogy, and
  re-identification.
- Do not apply or imply the repository's CC0 dedication to either data file.

## Decision

Eligible for GenomeSpy-managed hosting. This decision records eligibility; it
does not claim that the files have already been uploaded.

Reviewed: 2026-08-27
