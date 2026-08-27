# Data-rights review

## Scope

This review covers `castle_benchmarks.tar.gz` from Zenodo record 17780982 and
the five exact archive members identified in `provenance.json`. The proposed
outputs are:

- `severus-somatic.vcf`, an unchanged copy of the selected Severus VCF member;
  and
- `copy-numbers.tsv`, a transformed synchronization of the two selected Wakhan
  haplotype segment tables.

## Evidence and interpretation

The authoritative [versioned Zenodo record](https://zenodo.org/records/17780982)
identifies the deposit as version v1, names Ahmad Tanveer and Mikhail
Kolmogorov as creators, assigns the dataset
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), and reports the
archive's MD5 checksum. The record describes `castle_benchmarks` as outputs and
benchmarking scores for Wakhan's CASTLE analyses.

CC BY 4.0 permits sharing both transformations. The license requires
appropriate credit, a license link, and an indication of changes. The selected
archive members do not carry a conflicting notice.

## Conditions

- Credit Ahmad Tanveer and Mikhail Kolmogorov and cite the versioned Zenodo
  record and Wakhan paper.
- Link to CC BY 4.0 and do not imply endorsement.
- Identify `severus-somatic.vcf` as an unchanged archive member.
- Identify `copy-numbers.tsv` as a GenomeSpy-produced transformation and
  describe its coordinate conversion and ploidy-relative ratio.
- Do not impose legal or technical restrictions that conflict with CC BY 4.0.
- Do not imply that the recipe repository's CC0 dedication covers the data.

## Decision

Eligible for GenomeSpy-managed hosting under the conditions above.

Reviewed: 2026-08-27
