# ENCODE H3K27ac ChIP-seq GRCh38 integration fixture

This recipe pins 20 released ENCODE GRCh38 BigWigs containing H3K27ac
ChIP-seq fold-change-over-control signal. It is a durable engineering fixture
for GenomeSpy's SampleView-driven multi-URL loading, indexed-file range access,
sample filtering, metadata display, and faceting.

## Why this dataset

H3K27ac is a widely used marker of active regulatory regions. The selected
tracks give the integration prototype realistic, nonnegative signal with
different dynamic ranges across K562, HepG2, MCF-7, GM12878, A549, H1, and
umbilical-vein endothelial contexts. ENCODE supplies durable experiment and
file accessions plus structured metadata for auditing every input.

This selection is an engineering fixture, not a matched biological cohort.
The accepted files span six ENCODE experiments and several cell types, and
their production contexts are not controlled for comparative inference. File
accessions such as `ENCFF177JXC` identify tracks, not biological samples or
replicates.

Every accepted file is released, uses GRCh38, has target `H3K27ac`, output
category `signal`, and output type `fold change over control`. The historical
20-file order is pinned; ordinary runs never repeat the source-selection
heuristic.

## Run

Python 3.12 or newer is required. The ordinary command downloads missing
accepted BigWigs, writes compact sample metadata, and validates all outputs:

```bash
uv run --locked --script \
  recipes/encode-h3k27ac-chip-seq-grch38/scripts/prepare.py
```

The retained staging files can be reused without making another 5.17 GB copy.
This command creates ignored output symlinks and validates their targets:

```bash
uv run --locked --script \
  recipes/encode-h3k27ac-chip-seq-grch38/scripts/prepare.py \
  --source-directory /path/to/pinned-bigwigs
```

Use `--verify-only` to check existing outputs. To review what a current ENCODE
metadata query would select, run `--update-sources`; it writes an ignored
report and candidate table but never changes accepted provenance or downloads
BigWigs. Candidate changes require scientific and rights review before
acceptance.

## Outputs

- `output/bigwigs/<ENCODE-file-accession>.bigWig` contains each accepted file
  byte-for-byte.
- `output/samples.tsv` contains file accession, biosample label, organ terms,
  experiment accession, assembly, target, output type, byte size, and pipeline
  label.
- [`specs/overview.json`](specs/overview.json) uses relative URLs to exercise
  dynamic visible-sample expansion across all 20 files.

BigWig intervals use zero-based, half-open GRCh38 coordinates. The prototype
opens at `chr11:5200000-5400000`, a technical validation locus where every
accepted track contains finite positive signal. It is not presented as a
biologically selected comparison locus.

## Validation and limitations

The accepted run validates every ENCODE-reported byte size and MD5 plus a
local SHA-256, confirms BigWig structure and ten zoom levels, verifies selected
GRCh38 primary-chromosome lengths, and requires finite positive signal at the
initial locus. It also checks the deterministic sample table and aggregate
file-manifest fingerprint.

The files legitimately differ in their secondary contig sets: their BigWig
headers contain 99–138 chromosomes or contigs. Two accession pairs are
byte-identical (`ENCFF177JXC`/`ENCFF977KGH` and
`ENCFF289IVJ`/`ENCFF745TSK`) but remain separate because the accepted fixture
pins file-accession identity. Validation opens each BigWig in a separate
Python subprocess because pyBigWig 0.3.25 crashed during native cleanup after
all retained files were scanned sequentially in one process on the accepted
machine.

The fixture is large, heterogeneous, and unsuitable for comparative
biological inference. A fresh ENCODE query does not update the accepted
snapshot automatically.

## Data rights

The [rights review](RIGHTS.md) finds the released files eligible for
GenomeSpy-managed hosting under ENCODE's unrestricted-use policy, with ENCODE
Consortium, producing-laboratory, experiment, and file-accession credit.

Proposed release root:
`https://data.genomespy.app/datasets/encode-h3k27ac-chip-seq-grch38/v1/`.
