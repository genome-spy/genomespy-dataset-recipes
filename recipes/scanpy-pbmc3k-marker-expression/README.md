# Scanpy PBMC3k marker expression

Prepare the shared dataset behind the Python PBMC heatmap, expression tracks,
marker matrix, and two UMAP examples. The processed PBMC3k source provides a
small real single-cell dataset for comparing expression and cell annotations
across linked views. All five examples share one release.

## Run

```bash
uv run --locked --script recipes/scanpy-pbmc3k-marker-expression/scripts/prepare.py
```

The script pins Python and scientific dependencies, downloads the checksum-verified
cellxgene H5AD and the merged Python repository's preparation script, and runs
that producer in an isolated directory under `work/`. The producer is an external
MIT-licensed input, retained unchanged with its license; it is neither vendored
into CC0-covered paths nor reimplemented here. Cached inputs are checked on
every run. Missing inputs require network access; changed inputs fail closed.

For dependency-free offline validation of existing outputs:

```bash
python3 -S recipes/scanpy-pbmc3k-marker-expression/scripts/prepare.py --verify-only
```

## Outputs

- `output/pbmc-markers.json.gz`: the merged Python JSON payload, with canonical
  gzip headers. Includes 2,638 cells, twelve expression markers, six UMAP-panel
  markers, saved coordinates and labels, total counts, group summaries, tree
  segments, and display bounds. Expression and UMAP matrices share cell order.
- `output/CC-BY-4.0.txt` and `output/PYTHON-MIT-LICENSE.txt`: required accompanying
  notices for the data and the producer's contributions.

The JSON preserves existing Python field names for compatibility. It retains
saved `raw.X` log1p counts and `obsm.X_umap`; it does not rerun normalization,
clustering of cells, or UMAP. The producer computes group means, a single-linkage
Euclidean tree over those means, stable cell order within groups, and plotting
bounds. This is a preparation-only migration; no new prototype is introduced.

## Validation and limitations

The recipe checks exact input and output identities, the decoded merged-bundle
identity, matrix dimensions, finite/nonnegative expression, unique cell IDs,
group partitions, independently recomputed means, and display bounds. Recorded
parameters and software versions are in [provenance.json](provenance.json).
Gzip differs from the packaged file only in its OS header byte; decoded bytes
are identical. A new producer revision or changed scientific output requires
an explicit new release.

This is a curated teaching subset from one healthy donor. It is not a new
marker-discovery or differential-expression analysis. Original processed labels
and embedding coordinates are reused. Reproducing the processing before the
pinned H5AD is outside this recipe's scope.

## Data rights

The [rights review](RIGHTS.md) permits managed hosting with attribution and
modification notices. Provenance records the proposed versioned release root.
