# HCC1954: exploring Wakhan with GenomeSpy

[Wakhan](https://github.com/KolmogorovLab/Wakhan) infers chromosome-scale,
haplotype-specific copy number from long-read cancer sequencing. This demo
turns one published Wakhan result into a linked, zoomable GenomeSpy view.

## Data and purpose

The sample is the CASTLE **HCC1954 / HCC1954BL** PacBio HiFi tumor/normal pair
on **GRCh38**. The source is the published Wakhan run in
[Zenodo record 17780982 v1](https://zenodo.org/records/17780982), including its
rank-1 integer CN solution, Severus v1.7 somatic VCF, LOH calls, and archived
whole-genome Plotly figure.

The figure supplies 57,509 coverage and folded-BAF bins at 50 kb resolution.
The recipe extracts its literal data arrays without executing the HTML; it does
not rerun Wakhan or infer new copy numbers. Genomic context comes from UCSC
GRCh38 cytobands and 591 canonical cancer drivers from NCG 7.2, positioned with
NCBI RefSeq.

NCG was chosen instead of Wakhan's bundled default gene list. Wakhan's
[documentation](https://github.com/KolmogorovLab/Wakhan#genescopy-number-annotations)
describes that list as a freely available COSMIC Cancer Gene Census subset of
100 genes. The [current table](https://github.com/KolmogorovLab/Wakhan/blob/main/src/annotations/COSMIC_cancer_genes.tsv)
has 99 rows representing 98 unique symbols (`TBL1Y` occurs twice) and does not
record a COSMIC release, stable identifiers, or its selection method. NCG 7.2
is explicitly citable and freely downloadable, and its evidence table provides
the PubMed identifiers used here to rank labels.

This is a proof of concept based on published analysis artifacts. Some binned
measurements are available only inside the archived Plotly figure, so the
preparation is more specialized than a future importer for current Wakhan
output directories would be.

## Run the demo

From the **dataset-recipes repository root**:

```sh
uv run --script recipes/hcc1954-wakhan-explorer/scripts/prepare.py
uv run --script recipes/hcc1954-wakhan-explorer/scripts/serve.py
```

Open [the local demo](http://127.0.0.1:8082/specs/index.html). The page uses the
GenomeSpy 0.88.1 ESM bundle from jsDelivr. Once prepared, visualization data are
served locally; loading the page still requires access to jsDelivr.

The entry specification can also be opened in the GenomeSpy App development
server:

```text
http://127.0.0.1:8080/?spec=private/genomespy-dataset-recipes/recipes/hcc1954-wakhan-explorer/specs/explorer.json
```

## Specification

[`explorer.json`](specs/explorer.json) defines the shared genomic viewport,
styling, ruler, and interval selection. It imports focused track specifications:

| File | Contents |
| --- | --- |
| [`genome-navigator.json`](specs/genome-navigator.json) | Whole-genome navigation |
| [`structural-variants.json`](specs/structural-variants.json) | SV domes, breakpoint feet, insertions, and single breakends |
| [`copy-number.json`](specs/copy-number.json) | Shared CN autoscaling and the two haplotype tracks |
| [`haplotype.json`](specs/haplotype.json) | Reusable coverage/CN overlay |
| [`baf.json`](specs/baf.json) | Folded BAF and reference guides |
| [`segment-features.json`](specs/segment-features.json) | LOH intervals |
| [`blacklist.json`](specs/blacklist.json) | Reusable hatched source-mask layer |
| [`cytobands.json`](specs/cytobands.json) | Chromosome bands and labels |
| [`selected-genes.json`](specs/selected-genes.json) | Publication-ranked NCG drivers |

Keep the files together in `specs/`; their data URLs point to `../output/`.
The top-level `dataUrlPrefix` parameter controls that location, so a deployed
specification can instead use the versioned public data URL.

## Explore

- Use the locus buttons for useful starting points on chromosomes 8, 17, and
  21. The chromosome 8 views include a CN-33 HP2 segment near 106.59 Mb and the
  MYC neighborhood; the ERBB2 button opens its chromosome 17 context.
- Double-click and drag in the genome navigator to set its brush. Drag or scroll
  over the brush to move or resize it. Scroll and drag the detail tracks to zoom
  and pan their shared locus viewport.
- Shift-drag over a detail track to select an interval. Click or hover an SV to
  inspect it; selected arcs retain their class color while other arcs turn gray.
  Double-click empty space to clear a selection.
- Move over a detail track to show linked genomic and track-local rulers. The
  **Show ruler** checkbox controls them together, and rulers fade while the
  pointer is over the interval brush.
- Hover marks for source coordinates and attributes. CN rules show inferred
  states over the raw depth bins; SV tooltips include class, orientation,
  support, VAF, haplotype fields when available, and original identifiers.
- Gene labels appear as space permits. Their priority reflects the number of
  distinct NCG supporting publications, not significance in HCC1954.

All detail tracks remain synchronized. CN domains follow the current viewport,
and the depth axes are calibrated to them, so high-copy segments remain visible.
Raw depth bins may clip at the track edge. SVs load eagerly; arc height and
breakpoint feet adapt to zoom. **HP1 and HP2 are chromosome-local labels, not
maternal and paternal assignments.**

Hatched intervals are Wakhan source masks rather than zero-copy measurements.
Pale regions denote unavailable CN calls. LOH is shown in a compact track below
BAF so it does not obscure the measurements.

## Regenerate and verify

The first run downloads a 5.4 GB archive plus three small annotation files:

```sh
uv run --script recipes/hcc1954-wakhan-explorer/scripts/prepare.py
uv run --script recipes/hcc1954-wakhan-explorer/scripts/prepare.py --verify-only
uv run pytest tests/test_hcc1954_wakhan_explorer.py
uv run python tools/check_repo.py
```

To use an existing archive:

```sh
uv run --script recipes/hcc1954-wakhan-explorer/scripts/prepare.py \
  --archive /path/to/castle_benchmarks.tar.gz
```

Preparation verifies every downloaded file and selected archive member, writes
deterministic tables, and checks their accepted fingerprints. An interrupted
archive download resumes on the next run. Exact identities, parameters, output
checksums, validation results, and known events are in
[`provenance.json`](provenance.json).

The generated files in ignored `output/` are:

- `coverage-baf.tsv`
- `copy-number-segments.tsv`
- `loh-segments.tsv`
- `sv-links.tsv` and `sv-sites.tsv`
- `masked-regions.tsv` and `unavailable-cn.tsv`
- `cytobands.tsv` and `genes.tsv`

Coordinates are zero-based and half-open. Original VCF coordinates are retained
in the SV tables. Preparation explicitly selects the `wakhan_haplotagged` VCF
sample and accepts only `PASS`, fully called, alternate genotypes; both mates of
a BND must pass. Source `sBND` records are displayed in Wakhan's `BND` class
while retaining the original type.

## Limitations

- Coverage and BAF are 50 kb bin means extracted from the archived figure. BAF
  lacks per-SNP depth or support, so zero-valued bins remain ambiguous.
- Phasing confidence and reliable unphased depth are unavailable. No parental
  identity, phasing confidence, or subclonal fraction is inferred.
- Wakhan's LOH file contains intervals without confidence or allelic state.
- Exact source-mask placeholders are omitted from CN and LOH rather than shown
  as biological zero states. Other reported zero values remain visible.
- The selected genes are general NCG cancer drivers; their publication counts
  do not indicate alteration or significance in this sample.
- Dense rearrangements still overlap at whole-genome scale; zoom and selection
  provide detailed inspection.

## Attribution and rights

Data: Ahmad Tanveer and Mikhail Kolmogorov, Wakhan / CASTLE,
[Zenodo v1](https://doi.org/10.5281/zenodo.17780982),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Cite the
[Wakhan paper](https://doi.org/10.64898/2025.12.11.25342098) and
[Severus publication](https://doi.org/10.1038/s41587-025-02618-8).
Annotations: UCSC Genome Browser, NCBI RefSeq, and NCG 7.2; cite the
[NCG publication](https://doi.org/10.1186/s13059-022-02607-z).

The tables are transformed extracts and imply no author endorsement. See the
complete redistribution assessment in [`RIGHTS.md`](RIGHTS.md).
