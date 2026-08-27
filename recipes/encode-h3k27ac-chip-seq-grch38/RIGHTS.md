# Data-rights review

## Scope

This review covers the 20 unchanged released ENCODE H3K27ac ChIP-seq BigWigs
and the compact file-level `samples.tsv` derived from public ENCODE portal
metadata. Exact experiment and file accessions are recorded in
`provenance.json`.

## Evidence and interpretation

ENCODE's authoritative
[data-use policy](https://www.encodeproject.org/about/data-use-policy/) states
that released ENCODE datasets are available for unrestricted use immediately
upon public release. All accepted files are marked `released`, unrestricted,
and part of the ENCODE project; no file-specific restriction was found.

ENCODE's [citation guidance](https://www.encodeproject.org/help/citing-encode/)
requests credit to the ENCODE Consortium and producing laboratory, citation of
the current Consortium and portal publications, and identification of the
experiment (`ENCSR...`) and file (`ENCFF...`) accessions used.

The unrestricted-use policy permits mirroring these unchanged released
BigWigs and redistributing their compact public metadata under those
attribution conditions. The recipe repository's CC0 dedication does not apply
to either output class.

## Conditions

- Credit the ENCODE Consortium and the producing laboratories identified by
  the accepted experiment and file records.
- Identify the contributing `ENCSR...` experiments and `ENCFF...` files and
  link to the ENCODE portal.
- Cite the ENCODE publications requested by the current citation guidance.
- Describe the BigWigs as unchanged ENCODE files and `samples.tsv` as a
  GenomeSpy-produced compact metadata table.
- Do not imply that repository CC0 covers the data or that ENCODE endorses the
  mirror.

## Decision

Eligible for GenomeSpy-managed hosting under the conditions above.

Reviewed: 2026-08-27
