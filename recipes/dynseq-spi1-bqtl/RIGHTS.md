# Data-rights review

## Scope

This review covers the unchanged `chip_imp_ref.bw` and `chip_imp_alt.bw` files
at the immutable `dynseq-paper` commit recorded in `provenance.json`. No
repository source code or compact-slice derivative is included.

## Evidence and interpretation

The authoritative [Zenodo record 6582100](https://doi.org/10.5281/zenodo.6582100)
identifies the deposit as the “dynseq tracks data” dataset under CC BY 4.0. Its
description explicitly includes reference- and alternate-allele SPI1 variant-
analysis importance-score BigWigs and directs readers to the
[`dynseq-paper` repository](https://github.com/kundajelab/dynseq-paper).

The immutable Git tree at commit
[`febc9180d72e92302d35c549002e0d56c79c536e`](https://github.com/kundajelab/dynseq-paper/tree/febc9180d72e92302d35c549002e0d56c79c536e)
contains the two named files with the blob identities and sizes recorded in
provenance. We interpret the Zenodo dataset description and repository link as
establishing that its CC BY 4.0 terms cover these exact data files.

CC BY 4.0 permits sharing with attribution, a licence link, and an indication
of changes. These proposed outputs are unchanged copies. The recipe
repository's CC0 dedication does not apply to them.

## Conditions

- Credit Nair et al. and link Zenodo record 6582100.
- Link [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) and identify
  the files as unchanged copies from the pinned `dynseq-paper` commit.
- Retain the scientific citations and do not imply endorsement or clinical
  interpretation.
- Do not imply that the recipe repository's CC0 dedication covers the data.

## Decision

Use the authoritative immutable upstream URLs. Mirroring is permitted under
the conditions above, but no GenomeSpy-managed copy is currently needed.

Reviewed: 2026-08-27
