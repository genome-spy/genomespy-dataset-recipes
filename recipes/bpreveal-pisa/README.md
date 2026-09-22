# BPReveal PISA figure extracts

This recipe prepares compact Parquet extracts for prototyping the PISA
interaction visualizations in Figures 2c and 2d of McAnany and Zeitlinger,
*PISA: a versatile tool for visualizing cis-regulatory rules in genomic data*.

## Why this dataset

The authors' derived PISA results provide unusually direct examples of dense
base-to-base interaction matrices and sparse “squid” link diagrams. They are a
useful test of GenomeSpy's `rect` and `link` marks without rerunning model
training, DeepSHAP/PISA interpretation, motif discovery, or raw sequencing
processing.

The source is the authors' Zenodo record for the paper. The recipe downloads
the pinned derived-files archive and extracts only the HDF5, BigWig, and BED
members required for the shared Figure 2c/2d locus. HDF5 is an offline source
format only; every visualization-facing table is Snappy-compressed Parquet.

The locus uses dm6 coordinates.

## Run

The primary command is:

```bash
uv run --locked --script recipes/bpreveal-pisa/scripts/prepare.py
```

The download is approximately 28.4 GB, is resumable, and automatically retries
stalled or interrupted connections. `download/`, `work/`, and `output/` are
ignored and may be ordinary directories or symlinks. The archive is never
unpacked wholesale: one sequential pass extracts only the selected members.

Useful stages for recovery and inspection are:

```bash
uv run --locked --script recipes/bpreveal-pisa/scripts/prepare.py --stage download
uv run --locked --script recipes/bpreveal-pisa/scripts/prepare.py --stage index
uv run --locked --script recipes/bpreveal-pisa/scripts/prepare.py --stage extract
uv run --locked --script recipes/bpreveal-pisa/scripts/prepare.py --stage wrangle
uv run --locked --script recipes/bpreveal-pisa/scripts/prepare.py --stage verify
uv run --locked --script recipes/bpreveal-pisa/scripts/prepare.py --test
```

An already-downloaded archive can be supplied with `--archive PATH`.
The optional `index` stage writes the complete archive member list to the
ignored `work/archive-members.txt`; use it for source-path investigation
without repeatedly decompressing the archive.

## Outputs

The recipe creates:

- a sparse Figure 2c link table with `source`, `target`, and `effect`;
- a dense Figure 2d matrix table with `input`, `output`, and `effect`;
- base-resolution prediction and importance tracks;
- intersecting motif annotations; and
- `output/panels.json`, which records assemblies, locus coordinates, display
  spans, and thresholds.

Coordinates are zero-based. `source`, `target`, `input`, `output`, and
`position` identify single genomic bases. BED annotations remain zero-based,
half-open intervals. PISA effects are converted to log2 fold-change units,
matching BPReveal's plotting conversion.

The sparse link table retains exactly the Figure 2c absolute-effect threshold
of 0.03 in the paper notebook's native logit units.

## Local prototype

[`specs/fig2c-squid.json`](specs/fig2c-squid.json) recreates the main visual
encoding of Figure 2c using the sparse link, prediction, importance, and motif
Parquet outputs. It uses straight `link` marks from input bases to output
positions, with positive effects in red and negative effects in blue. The
prediction and input-contribution profiles use one-base `rect` marks.

The accepted local Figure 2c extract contains 5,093 links, 1,502 profile rows,
and six motif calls. The link table is 42 KB and renders interactively in the
local GenomeSpy application.

## Validation and limitations

The workflow verifies the source archive's published size and MD5, records
SHA-256 identities for every extracted member, validates HDF5 dimensions,
checks coordinate bounds and finite values, and validates every Parquet schema
and record count after writing.

The shared Figure 2c/2d locus has an accepted local run recorded in
`provenance.json`. The cached archive index confirms that the deposit does not
contain the PISA HDF5 matrices used for Figures 2a, 2b, and 3b; reproducing
those panels would require additional upstream analysis, so they are excluded
from this recipe. The motif table contains all annotations intersecting the
displayed locus rather than only the subset emphasized in the paper. Reference
sequence letters are not extracted in this initial output contract.

## Data rights

See [`RIGHTS.md`](RIGHTS.md). Redistribution remains unresolved, so generated
outputs are local-only unless the rights record is updated with authoritative
evidence.
