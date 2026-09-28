# HapMap association teaching table

This recipe acquires the historical manhattanly table used by the Python
Manhattan, volcano, and linked-genome examples. It preserves the accepted CSV
exactly, so moving storage does not change plotted results.

Coordinates and variant identifiers come from HapMap build 36, with UCSC hg18
gene annotations. Association p-values and effect sizes are simulated; this
is not a measured disease association study and contains no individual genotypes.
Credit Sahir Bhatnagar, HapMap, UCSC, and Vince Forgetta's annotation work.

## Preparation

```bash
uv run --script recipes/manhattanly-hapmap-associations/scripts/prepare.py
uv run --script recipes/manhattanly-hapmap-associations/scripts/prepare.py --verify-only
```

The normal command downloads pinned sources into `download/`, validates them,
and writes unchanged artifacts into `output/`. Existing cached inputs must
match their recorded hashes. `--source-dir PATH` accepts already downloaded
inputs with the filenames in provenance. Verification uses no network.

Outputs are `hapmap-associations.csv`, `LICENSE-MIT.txt`, and
`UPSTREAM-COPYRIGHT.txt`. `specs/overview.json` is a local point-plot smoke spec;
the Python gallery retains its existing preparation, composition, and styling.

This reproduces the accepted historical table's acquisition, not the original
sampling/simulation pipeline: its external helper and original annotation
intermediate are not available. No statistics are regenerated and no GenomeSpy
upstream example or hosted file is changed. Moving the Python gallery's derived
tables into recipe outputs is a later step.

See [provenance](provenance.json) for exact identities and validation, and
[rights](RIGHTS.md) for the hosting decision and attribution conditions.
The recipe repository's CC0 dedication does not license these data.
