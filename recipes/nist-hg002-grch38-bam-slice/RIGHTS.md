# Data-rights review

## Scope

This review covers the NIST GIAB HG002 / NA24385 GRCh38 300x parent BAM and BAI
identified in `provenance.json` and the recipe's downsampled regional BAM/BAI
pair.

## Evidence and interpretation

The authoritative [NIST Genome in a Bottle project page](https://www.nist.gov/programs-projects/genome-bottle)
states that the Ashkenazi Jewish and Han Chinese Personal Genome Project trios
were consented for commercial redistribution. The pinned GIAB index identifies
the exact files and reported checksums. Zook et al.,
[Extensive sequencing of seven human genomes](https://doi.org/10.1038/sdata.2016.25),
describes the samples, consent, and benchmark purpose. This supports public
redistribution of the much smaller derived slice, but does not make genomic data
anonymous or risk-free.

## Conditions

- Credit NIST Genome in a Bottle and identify HG002 / NA24385.
- Link to the NIST page, pinned source index, and cited paper.
- Describe the pair as a GenomeSpy-produced regional, downsampled extract.
- Preserve warnings against clinical interpretation, genealogy, and
  re-identification.
- Do not imply that repository CC0 covers the data.

## Decision

Eligible for GenomeSpy-managed hosting under the conditions above.

Reviewed: 2026-08-27
