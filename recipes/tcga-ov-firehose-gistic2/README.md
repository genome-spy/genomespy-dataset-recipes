# TCGA-OV Firehose GISTIC2

This recipe exposes two unchanged files from the Broad Institute GDAC
Firehose GISTIC2 analysis of the TCGA ovarian serous cystadenocarcinoma cohort
(`OV-TP`). The accepted archive is the 2016-01-28 analysis release
`2016012800.0.0`, produced with GISTIC 2.0.22 on hg19.

## Why this dataset

GISTIC summarizes copy-number changes that recur across a tumour cohort. The
two accepted files support complementary GenomeSpy views: `scores.gistic`
shows the genome-wide strength of amplifications and deletions, while
`all_lesions.conf_99.txt` distinguishes each significant lesion's wide peak,
peak, and containing region. The recipe-local spec initially focuses on
chromosomes 18–20 so that nested intervals and nearby score changes are easy
to inspect, while remaining freely navigable across hg19.

The source was selected because it is the exact legacy dataset used by the
maintained GenomeSpy TCGA-OV GISTIC example. Migration preserves its source
identity and display semantics without changing the deployed spec.

## Run

Python 3.12 or newer is required. The ordinary command downloads the pinned
archive when needed, verifies it, and extracts only the two accepted members:

```bash
uv run --script recipes/tcga-ov-firehose-gistic2/scripts/prepare.py
```

An existing archive can be used in place without copying it:

```bash
uv run --script recipes/tcga-ov-firehose-gistic2/scripts/prepare.py \
  --archive /path/to/gdac.broadinstitute.org_OV-TP.CopyNumber_Gistic2.Level_4.2016012800.0.0.tar.gz
```

Use `--verify-only` to validate existing outputs without reading or downloading
the archive.

Preparation is intentionally limited to byte-identical extraction. No rows or
columns are selected, no coordinates are converted, and no liftover is
performed. The display-time transforms in the spec sign deletion scores,
select the three lesion limit fields, and parse their reported intervals.

## Outputs

- `output/scores.gistic` is the unchanged 90,240-row GISTIC score table.
  Chromosomes are numbered 1–23, where the source uses 23 for X.
- `output/all_lesions.conf_99.txt` is the unchanged 146-row all-lesions table.
  Its wide-peak, peak, and region strings use hg19 base-pair coordinates and
  retain the appended GISTIC probe-index ranges.
- [`specs/overview.json`](specs/overview.json) loads both files through relative
  `../output/...` URLs.

The source documentation does not establish whether reported interval ends
are inclusive. The recipe therefore preserves the coordinates exactly and
does not claim a half-open or closed convention.

## Validation and limitations

The accepted run verifies the archive's byte size, MD5, and SHA-256; both
member paths, sizes, MD5s, and SHA-256s; and the absence of the previously
expected `regions_track.conf_99.bed`. It checks the exact headers and row
counts, numeric finiteness and interval order in the score table, 33
amplification and 40 deletion peaks in each of the primary and `CN values`
sections, and all 438 parseable lesion intervals. The spec uses only the 73
primary peak rows.

The all-lesions header contains 579 named TCGA tumour-sample columns plus a
trailing blank column. The archive's `arraylistfile.txt` has the same 579 names
after its `Array` header. This source-format quirk is preserved rather than
repaired. The output retains sample identifiers and is intended for aggregate
visualization, not patient-level interpretation. The cohort and hg19 analysis
are a historical snapshot, and the significance scores are not clinical
evidence.

## Data rights

The [rights review](RIGHTS.md) finds no explicit permission to mirror these
exact Broad-produced archive members. The outputs therefore remain local-only.
The TCGA Research Network acknowledgment requested by NCI must accompany any
permitted use.
