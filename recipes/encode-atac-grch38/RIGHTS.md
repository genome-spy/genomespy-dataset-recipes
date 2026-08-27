# Data-rights review

## Scope

This review covers the 24 unchanged released ENCODE BigWigs and the compact
file-level `samples.tsv` derived from their public portal metadata. Exact file
and annotation accessions are recorded in `provenance.json`.

## Evidence and interpretation

ENCODE's authoritative
[data-use policy](https://www.encodeproject.org/about/data-use-policy/) states
that released ENCODE datasets are available for unrestricted use immediately
upon public release. All accepted files are marked `released`, unrestricted,
and part of the ENCODE project; no file-specific restriction was found.

ENCODE's [citation guidance](https://www.encodeproject.org/help/citing-encode/)
requests credit to the ENCODE Consortium and producing laboratory, citation of
the current Consortium and portal publications, and identification of the
dataset (`ENCSR...`) and file (`ENCFF...`) accessions used.

The unrestricted-use policy covers mirroring the unchanged released BigWigs
and redistributing their compact public metadata under those attribution
conditions. The recipe repository's CC0 dedication does not apply to either
output class.

## Conditions

- Credit the ENCODE Consortium and the Anshul Kundaje lab at Stanford.
- Identify the contributing `ENCSR...` datasets and `ENCFF...` files and link
  to the ENCODE portal.
- Cite the ENCODE publications requested by the current citation guidance.
- Describe the BigWigs as unchanged ENCODE files and `samples.tsv` as a
  GenomeSpy-produced compact metadata table.
- Do not imply that repository CC0 covers the data or that ENCODE endorses the
  mirror.

## Decision

Eligible for GenomeSpy-managed hosting under the conditions above.

Reviewed: 2026-08-27
