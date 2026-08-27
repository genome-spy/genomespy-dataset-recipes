# ASCAT simulated tumors on hg19

This recipe prepares nine tumor profiles from ASCAT's official simulated hg19
example data. One GenomeSpy spec combines allele-specific copy number, LogR,
and B-allele frequency for S96; another explores purity/ploidy fits across all
nine samples.

## Why this dataset

The source is [VanLoo-lab/ascat](https://github.com/VanLoo-lab/ascat) commit
`61ddf3b24453eea91134798cc41d4e828a82fa90` (ASCAT 3.2.0). Simulated profiles
avoid patient measurements while retaining realistic segmentation and
purity/ploidy behavior.

The selected samples span purity 0.24–1.0 and ploidy 1.7–3.4. S96 has a varied
84-segment whole-genome profile. Together, the tables demonstrate coordinated
interval and point tracks, linked parameters, calculated copy numbers, and an
interactive objective surface. This recipe replaces an older hg18 example with
the maintained hg19 source.

## Run

Requirements are R 4.5.2, ASCAT 3.2.0, and `gzip`. Place the six pinned files
listed in `provenance.json` under `download/`, then run:

```bash
Rscript recipes/ascat-simulated-tumors-hg19/scripts/prepare.R
```

This builds the ASCAT object, wrangles the tables, and validates them. For the
optional comparison with ASCAT's fitting-distance implementation, set
`ASCAT_SOURCE_DIR` to a checkout of the pinned commit before running the same
command. The checkout is used as a dependency; no ASCAT source is copied here.

## Outputs

- `output/fits.tsv.gz` — accepted solution for each selected sample;
- `output/samples/<sample>/segments.tsv.gz` — allele-specific calls;
- `output/samples/<sample>/fit-segments.tsv.gz` — segmented LogR/BAF runs;
- `output/samples/<sample>/raw.tsv.gz` — 10,000 probe-level values.

Chromosomes use hg19 names without `chr`. Probe positions are one-based;
segment ends are inclusive. The specs are
[`copy-number-overview.json`](specs/copy-number-overview.json) and
[`purity-ploidy-fitting.json`](specs/purity-ploidy-fitting.json).

## Validation and limitations

All nine samples are checked against saved ASCAT objects. A clean source run
reproduced the accepted intermediate, consecutive wrangling runs were
byte-identical, and the GenomeSpy fitting objective matched ASCAT 3.2.0 to
floating-point precision. Exact fingerprints and sample counts are in
`provenance.json`.

## Data rights

The [rights review](RIGHTS.md) permits hosting with the upstream GPL notice,
source link, attribution, and citation preserved.

Proposed release root:
`https://data.genomespy.app/datasets/ascat-simulated-tumors-hg19/v1/`. The
`samples/<sample>/...` layout is preserved below it.
