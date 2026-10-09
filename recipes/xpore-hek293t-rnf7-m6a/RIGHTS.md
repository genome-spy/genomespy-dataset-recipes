# Data-rights review

## Scope

This review covers `rnf7-direct-rna.json.gz`, a reduced and reformatted extract
of RNF7 alignment geometry, read-level alignment events, and exon annotations
from the xPore demo archive, combined with selected RNF7 rows from m6Anet
Supplementary Table 6 and 920 bases reconstructed from three GRCh38 exon
sequences returned by Ensembl. It does not cover or redistribute raw FAST5
signal, complete FASTQ or BAM files, or the complete supplementary table.

## Evidence and interpretation

The authoritative [Zenodo record 4587661](https://doi.org/10.5281/zenodo.4587661)
identifies *xPore: Identification of differential RNA modifications from
nanopore direct RNA sequencing* under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The accepted demo
archive is pinned to Zenodo record 5707193 in `provenance.json`.

Hendra et al., [*Detection of m6A from direct RNA sequencing using a multiple
instance learning framework*](https://doi.org/10.1038/s41592-022-01666-1),
publishes Supplementary Table 6 with the article. The article's rights statement
licenses the article and included supplementary material under CC BY 4.0 unless
separately credited; the table has no separate restrictive credit.

The authoritative [Ensembl data disclaimer](https://www.ensembl.org/info/about/legal/disclaimer.html)
states that Ensembl imposes no restrictions on access to or use of data it
provides, while noting that third-party constraints may apply. The three small
GRCh38 sequence responses are pinned individually in `provenance.json`; no
separate restriction is attached to those reference bases.

CC BY 4.0 permits sharing and adaptation with attribution, a license link, and
an indication of changes. The proposed output is a substantially reduced,
reformatted derivative. The recipe repository's CC0 dedication does not apply
to the data.

## Conditions

- Credit Pratanwanich et al. for xPore, Hendra et al. for m6Anet, and Ensembl
  for the GRCh38 sequence service.
- Link the two publications, Zenodo record 4587661, and CC BY 4.0.
- State that GenomeSpy extracted RNF7, reduced alignments to display geometry
  and alignment events, reconstructed transcript sequence from the demo GTF's
  GRCh38 exon intervals, pseudonymized read labels, calculated coverage, and
  reformatted the tables.
- Do not imply that the recipe repository's CC0 dedication covers the output.

## Decision

Eligible for GenomeSpy-managed hosting under the conditions above.

Reviewed: 2026-09-15
