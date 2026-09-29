# Data rights

## Scope and evidence

This record covers UCSC's hg19 and hg38 `refGene` tables identified in provenance
and the derived gene-body CSV. [UCSC's data terms](https://genome.ucsc.edu/license/)
allow public and commercial use of raw database tables, subject to provider
restrictions. These RefSeq gene annotations are distinct from restricted clinical
annotation tracks. The Python project's existing notice credits UCSC and NCBI.

## Interpretation and conditions

The output collapses transcript intervals and counts transcripts; it does not
include controlled-access data. Retain UCSC and NCBI RefSeq attribution and
identify the assembly, coordinate convention, and collapse operation. Preserve
the authoritative source links and input identities in release provenance.
The recipe's CC0 dedication does not relicense adjacent data.

## Decision

Eligible for GenomeSpy-managed hosting under the conditions above.

Reviewed: 2026-09-28
