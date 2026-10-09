# Data-rights review

## Scope

A reduced, reformatted extract of Scanpy's processed PBMC3k fixture from the
pinned cellxgene H5AD: selected log1p expression, saved UMAP coordinates, cell
labels and counts, with derived group means, tree, ordering and display metadata.
The full H5AD and downloaded preparation software are not publication artifacts.

## Evidence and interpretation

The authoritative [10x PBMC3k dataset page](https://www.10xgenomics.com/datasets/3-k-pbm-cs-from-a-healthy-donor-1-standard-1-1-0)
licenses the source data under CC BY 4.0. The processed fixture is pinned to
[cellxgene revision 68dfbcc](https://github.com/chanzuckerberg/cellxgene/blob/68dfbcc2eb675e96c6a5e2a6b7a0d3465ccf46bc/example-dataset/pbmc3k.h5ad).
The merged [Python provenance notice](https://github.com/genome-spy/genome-spy-python/blob/fd3a272ecad54dbf92bf1a7390c0d627d346296b/THIRD_PARTY_NOTICES.md)
identifies Scanpy preprocessing and carries the 10x attribution. Its
[MIT license](https://github.com/genome-spy/genome-spy-python/blob/fd3a272ecad54dbf92bf1a7390c0d627d346296b/LICENSE)
covers the downloaded producer; it does not relicense the biological data.
CC BY 4.0 permits sharing and adaptation with attribution and a changes notice.

## Conditions

Credit 10x Genomics, Scanpy's preprocessing contributors, cellxgene's distribution,
and GenomeSpy Python's derived display tables. Link the original data and
CC BY 4.0. Disclose marker selection, retained source embedding/labels, derived
group means and tree, stable ordering and display bounds. Publish both notice
files in the inventory alongside the bundle. Retain the MIT notice with local
copies of the producer. The recipe repository's CC0 dedication applies only to
original orchestration and metadata, never to the source data, software or
published extract.

## Decision

Eligible for GenomeSpy-managed hosting under the conditions above.

Reviewed: 2026-10-09
