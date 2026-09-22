# BPReveal PISA figure extracts

This recipe prepares compact Parquet extracts for prototyping the PISA
interaction visualizations in Figures 2a–d and the left-hand part of Figure 3b
of McAnany and Zeitlinger, *PISA: a versatile tool for visualizing
cis-regulatory rules in genomic data*.

## Why this dataset

The authors' derived PISA results provide unusually direct examples of dense
base-to-base interaction matrices and sparse “squid” link diagrams. They are a
useful test of GenomeSpy's `rect` and `link` marks without rerunning model
training, DeepSHAP/PISA interpretation, motif discovery, or raw sequencing
processing.

The source is the authors' Zenodo record for the paper. The recipe downloads
the pinned derived-files archive and extracts only the HDF5, BigWig, and BED
members required for the selected figure loci. HDF5 is an offline source
format only; every visualization-facing table is Snappy-compressed Parquet.

The mouse panels use mm10 coordinates and the fly panels use dm6 coordinates.

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
uv run --locked --script recipes/bpreveal-pisa/scripts/prepare.py --stage extract
uv run --locked --script recipes/bpreveal-pisa/scripts/prepare.py --stage wrangle
uv run --locked --script recipes/bpreveal-pisa/scripts/prepare.py --stage verify
uv run --locked --script recipes/bpreveal-pisa/scripts/prepare.py --test
```

An already-downloaded archive can be supplied with `--archive PATH`.

## Outputs

The recipe creates:

- sparse link tables for Figures 2a–c, with `source`, `target`, and `effect`;
- dense matrix tables for Figures 2d and 3b, with `input`, `output`, and
  `effect`;
- base-resolution prediction and importance tracks for each locus;
- intersecting motif annotations; and
- `output/panels.json`, which records assemblies, locus coordinates, display
  spans, and thresholds.

Coordinates are zero-based. `source`, `target`, `input`, `output`, and
`position` identify single genomic bases. BED annotations remain zero-based,
half-open intervals. PISA effects are converted to log2 fold-change units,
matching BPReveal's plotting conversion.

The sparse tables retain exactly the absolute-effect thresholds used by the
paper notebooks: 0.35 in the notebooks' native logit units for Figures 2a and
2b and 0.03 for Figure 2c. Positive and negative strand matrices are summed
for Figures 2a and 2b before thresholding.

## Validation and limitations

The workflow verifies the source archive's published size and MD5, records
SHA-256 identities for every extracted member, validates HDF5 dimensions,
checks coordinate bounds and finite values, and validates every Parquet schema
and record count after writing.

The recipe has not yet had an accepted full run, so output fingerprints and
observed sparse-link counts remain to be recorded in `provenance.json`. Motif
tables contain all annotations intersecting each displayed locus; the later
GenomeSpy specification may select or recolor the subset emphasized in the
paper. Reference sequence letters are not extracted in this initial output
contract.

## Data rights

See [`RIGHTS.md`](RIGHTS.md). Redistribution remains unresolved, so generated
outputs are local-only unless the rights record is updated with authoritative
evidence.
