# Data-rights review

## Scope

The input is the authors' `zenodo-bpreveal-files.tar.bz2` archive from Zenodo
record 20318019. The recipe extracts selected derived PISA HDF5 matrices,
predicted and importance BigWigs, and motif BED files. Its outputs are small
locus-specific Parquet transformations for Figures 2a–d and the left-hand
portion of Figure 3b.

## Evidence and interpretation

- Paper: <https://doi.org/10.1038/s41467-026-74807-1>
- Zenodo record: <https://zenodo.org/records/20318019>
- Stowers publication record: <https://www.stowers.org/research/publications/libpb-2546>

The Zenodo record labels the deposit GPL-2.0-or-later, while the archive also
contains derived results based on several third-party experimental datasets.
The available record does not yet establish clearly that the proposed reduced
data extracts may be redistributed independently under that software license.
Public accessibility and the paper's CC BY license are not sufficient evidence
for mirroring the underlying data.

## Conditions

Retain citation of the paper, the Zenodo record, and the originating
experimental datasets. Determine the controlling terms for the selected
derived data before any public hosting.

## Decision

Local-only: unresolved.

The recipe may be run locally, but its generated outputs must not be uploaded
to GenomeSpy-managed storage until authoritative redistribution evidence is
recorded here.

Reviewed: 2026-09-21
