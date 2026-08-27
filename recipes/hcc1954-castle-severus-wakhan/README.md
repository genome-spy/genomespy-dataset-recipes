# HCC1954 CASTLE Severus and Wakhan

This recipe pairs somatic structural variants called by Severus with
haplotype-specific copy-number segments inferred by Wakhan for the HCC1954 /
HCC1954BL tumour-normal cell-line pair. Both inputs come from the same PacBio
HiFi Wakhan run in Zenodo record
[17780982](https://zenodo.org/records/17780982).

## Why this dataset

The selected source is the exact Severus v1.7 VCF that Wakhan used as its
breakpoint input, rather than a newer compact HCC1954 callset whose records do
not match this copy-number analysis. Wakhan's rank-1 solution
`4.57_0.99_0.9` has DNA purity 1.00, cell purity 0.99, ploidy 4.57, and
confidence 0.90.

The data use GRCh38 coordinates and contain dense intra- and interchromosomal
rearrangements together with large copy-number changes. They demonstrate how
GenomeSpy can pair VCF-derived SV arcs with a synchronized quantitative track.
The local spec initially spans a complex chromosome 21–22 region; other
reported rearrangements around TERT, APC, and MYC can be explored by changing
the domain.

The maintained GenomeSpy
[`hcc1954-sv-cnv.json`](https://github.com/genome-spy/genome-spy/blob/master/examples/docs/examples/genomic-data/hcc1954-sv-cnv.json)
consumer pairs the VCF directly. No maintained consumer uses the staging-only
`sv-links.tsv`, so this recipe intentionally omits that obsolete transform.

## Run

Python 3.12 or newer is required. The ordinary command downloads and verifies
the pinned 5.4 GB Zenodo archive when it is not already cached:

```bash
uv run --script recipes/hcc1954-castle-severus-wakhan/scripts/prepare.py
```

To reuse an existing copy without duplicating it, pass its path explicitly:

```bash
uv run --script recipes/hcc1954-castle-severus-wakhan/scripts/prepare.py \
  --archive /path/to/castle_benchmarks.tar.gz
```

The script verifies the archive, extracts only five pinned members into the
ignored `work/` directory, copies the VCF byte-for-byte, and intersects the two
haplotype segmentations to generate total copy number.
Use `--verify-only` to validate existing outputs against `provenance.json`.

## Outputs

- `output/severus-somatic.vcf` is the byte-identical Severus v1.7 source
  member. VCF positions are one-based anchors as defined by VCF 4.2.
- `output/copy-numbers.tsv` contains the synchronized haplotype segments used
  by [`specs/overview.json`](specs/overview.json). Its `start` and `end` fields
  are zero-based, half-open coordinates. `relative_copy_ratio` is total integer
  copy number divided by the selected ploidy estimate, 4.57.

The `sv_breakpoint_ids` field preserves the two source annotations as text. It
is provenance context rather than a normalized relational field.

## Validation and limitations

The accepted VCF contains 1,766 `PASS` records, including 692 complete BND
mate pairs. The copy-number output has 1,189 sorted positive intervals across
autosomes `chr1`–`chr22`. Exact input identities, output fingerprints, type
counts, ranges, and source-linkage evidence are in `provenance.json`.

HCC1954 is a highly rearranged cancer cell line, not a representative normal
genome. Wakhan's ploidy-relative ratio is a visualization normalization, not a
measured tumour-versus-normal logR. The recipe does not reproduce Severus or
Wakhan from reads. The source copy-number grids stop at rounded analysis
boundaries before the ends of the GRCh38 autosomes; the recipe preserves those
uncovered terminal tails rather than filling them. It is not suitable for
clinical interpretation or caller benchmarking.

## Data rights

The [rights review](RIGHTS.md) finds both transformed outputs eligible for
GenomeSpy-managed hosting under CC BY 4.0
attribution and change-marking conditions.

Proposed release root:
`https://data.genomespy.app/datasets/hcc1954-castle-severus-wakhan/v1/`.
