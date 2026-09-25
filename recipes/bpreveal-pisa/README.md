# BPReveal PISA figure extracts

This recipe prepares compact Parquet extracts for prototyping the PISA
interaction visualizations in Figures 2c and 2d of McAnany et al.,
*Positional interpretation of cis-regulatory code and nucleosome organization
with deep learning models*.

## Why this dataset

The authors' derived PISA results provide unusually direct examples of dense
base-to-base interaction matrices and sparse “squid” link diagrams. They are a
useful test of GenomeSpy's `rect` and `link` marks without rerunning model
training, DeepSHAP/PISA interpretation, motif discovery, or raw sequencing
processing.

The source is the authors' Zenodo record for the paper. The recipe downloads
the pinned derived-files archive and extracts only the HDF5, BigWig, BED, and
PISA-input FASTA members required for the shared Figure 2c/2d locus. HDF5 and
FASTA are offline source formats only; every visualization-facing table is
Snappy-compressed Parquet.

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
- base-resolution prediction and importance tracks with reference bases;
- intersecting motif annotations; and
- `output/panels.json`, which records assemblies, locus coordinates, display
  spans, and thresholds.

Coordinates are zero-based. `source`, `target`, `input`, `output`, and
`position` identify single genomic bases. BED annotations remain zero-based,
half-open intervals. PISA effects are converted to log2 fold-change units,
matching BPReveal's plotting conversion.

Each source FASTA header identifies the first PISA output position, while its
2,114-base sequence begins 557 bases earlier to supply the model's input
context. The recipe removes that padding before associating reference bases
with track positions.

The sparse link table retains exactly the Figure 2c absolute-effect threshold
of 0.03 in the paper notebook's native logit units.

## Local prototype

[`specs/fig2c-squid.json`](specs/fig2c-squid.json) recreates the main visual
encoding of Figure 2c using the sparse link, prediction, importance, and motif
Parquet outputs. It uses straight `link` marks from input bases to output
positions, with positive effects in red and negative effects in blue. The
prediction profile uses one-base `rect` marks. The contribution profile uses
the same bars in the overview and switches to a base-colored Dynseq logo when
each base is at least 12 pixels wide.

[`specs/fig2d-matrix.json`](specs/fig2d-matrix.json) renders the corresponding
Figure 2d PISA matrix as 541,501 one-base `rect` marks. It retains the paper's
diverging effect colors and clipped-value colors, places the accessibility
profile to the right, overlays motif intervals near the bottom of the matrix,
and places the contribution track below it. The contribution bars likewise
switch to a Dynseq logo at 12 pixels per base. Shared positional scales keep
both margin profiles aligned with the matrix during navigation. Picking and
the mark's spatial search index are disabled for the dense matrix marks to
reduce their runtime overhead. When zoomed in sufficiently, a collected data
branch reactively filters to the visible matrix tiles and adds formatted effect
labels without instantiating text for the full matrix.

The accepted local Figure 2c/2d extract contains 5,093 links, 1,502 profile rows,
and six motif calls. The link table is 42 KB; the Figure 2d matrix table is
2.7 MB. Both prototypes use the same accepted local extract.

## Validation and limitations

The workflow verifies the source archive's published size and MD5, records
SHA-256 identities for every extracted member, validates HDF5 dimensions,
checks coordinate bounds, FASTA padding, and finite values, and validates every
Parquet schema and record count after writing.

The shared Figure 2c/2d locus has an accepted local run recorded in
`provenance.json`. The cached archive index confirms that the Zenodo archive
does not contain the PISA HDF5 matrices used for Figures 2a, 2b, and 3b. It does
include the trained OSKN and H3K27ac models, analysis configurations, and
supporting tracks. The paper also states that raw PISA values are available
from Stowers Original Data Repository record
[`LIBPB-2546`](https://www.stowers.org/research/publications/libpb-2546), but
its packaging and practical download size have not been evaluated. If direct
retrieval is not practical, the missing locus-scale matrices could be
regenerated with BPReveal's `interpretPisa` without retraining. Linux with an
NVIDIA GPU is the simplest option; CPU execution is slower, while DGX Spark
requires a compatible ARM64 TensorFlow/CUDA environment. Those analyses are
outside the current recipe. The motif table contains all annotations
intersecting the displayed locus rather than only the subset emphasized in the
paper.

## Data rights

See [`RIGHTS.md`](RIGHTS.md). The four Parquet extracts are eligible for
GenomeSpy-managed hosting under `GPL-2.0-or-later` with the recorded notices,
attribution, and source citations. The repository's CC0 dedication does not
license the data.
