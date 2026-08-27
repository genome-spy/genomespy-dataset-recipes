# ENCODE ATAC GRCh38 integration fixture

This recipe pins 24 released ENCODE GRCh38 BigWigs containing normalized
observed ATAC-seq signal profiles. It is a durable engineering fixture for
GenomeSpy's SampleView-driven multi-URL lazy loading, parallel indexed-file
access, sample filtering, metadata display, and faceting.

## Why this dataset

ENCODE supplies stable file and dataset accessions, structured biosample
metadata, and realistic BigWigs large enough to exercise browser range access.
The accepted selection deliberately mixes cell lines, primary immune cells,
and vascular tissues. That variety is useful for technical filtering and
metadata tests, but it is not a biologically controlled cohort.

Every selected file is a released GRCh38 `bigWig` with output category
`signal`, output type `normalized observed signal profile`, assay term
`ATAC-seq`, and annotation type `ChromBPNet-model`. All were produced by the
Anshul Kundaje lab at Stanford. The accepted 24-file order is pinned; ordinary
runs never repeat the heuristic selection.

File accessions such as `ENCFF357WGX` are stable track identifiers. They are
not biological sample IDs, and repeated biosample labels do not imply matched
donors, replicates, or processing contexts.

## Run

Python 3.12 or newer is required. The ordinary command downloads missing
accepted BigWigs, writes compact sample metadata, and validates all outputs:

```bash
uv run --locked --script recipes/encode-atac-grch38/scripts/prepare.py
```

The retained staging files can be reused without another 6.9 GB copy. This
creates ignored output symlinks and validates their targets:

```bash
uv run --locked --script recipes/encode-atac-grch38/scripts/prepare.py \
  --source-directory /path/to/pinned-bigwigs
```

Use `--verify-only` to check existing outputs. To review what a fresh metadata
query would select, run `--update-sources`; it writes an ignored report and
candidate table but never changes the accepted provenance or downloads
BigWigs. Candidate changes require scientific and rights review before they are
accepted.

## Outputs

- `output/bigwigs/<ENCODE-file-accession>.bigWig` contains each accepted file
  byte-for-byte.
- `output/samples.tsv` contains file accession, biosample label, organ terms,
  dataset accession, assembly, output type, byte size, and producing lab.
- [`specs/overview.json`](specs/overview.json) uses relative URLs to exercise
  dynamic visible-sample expansion across all 24 files.

BigWig intervals use the standard zero-based, half-open convention on
GRCh38/hg38. The prototype opens around the ACTB locus at
`chr7:5520000-5570000`, where every accepted track has finite positive signal.

## Validation and limitations

The accepted run validates each ENCODE-reported byte size and MD5 plus a local
SHA-256, confirms all 24 files open as BigWig with the expected GRCh38 primary-
chromosome lengths, and checks finite positive signal at the initial ACTB
locus. It also verifies the deterministic sample table and the aggregate file
manifest fingerprint.

The source files include many intervals whose score is IEEE NaN. GenomeSpy's
positive-score filter excludes those values; the validator requires both the
known non-finite values and usable finite signal at the initial locus. The
fixture is large, mixes annotation datasets and biological contexts, and is
unsuitable for comparative biological inference. File-size and metadata
changes from a new ENCODE query do not update this accepted snapshot
automatically.

## Data rights

The [rights review](RIGHTS.md) finds the released files eligible for
GenomeSpy-managed hosting under ENCODE's unrestricted-use policy, with ENCODE
Consortium, production-lab, dataset, and file-accession credit.

Proposed release root:
`https://data.genomespy.app/datasets/encode-atac-grch38/v1/`.
