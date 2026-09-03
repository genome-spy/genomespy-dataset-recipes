# HCC1954: exploring Wakhan with GenomeSpy

[Wakhan](https://github.com/KolmogorovLab/Wakhan) uses long reads to correct
phase switches and infer chromosome-scale, haplotype-specific cancer copy
number. This local demonstration explores how its results can become a linked,
zoomable genomic view in GenomeSpy. It uses existing GenomeSpy features and
changes no GenomeSpy source code.

## Data and purpose

The sample is the CASTLE **HCC1954 / HCC1954BL** tumour/normal cell-line pair,
PacBio HiFi, **GRCh38**. Inputs come from the same published Wakhan run in
[Zenodo record 17780982, v1](https://zenodo.org/records/17780982): rank-1 solution
`4.57_0.99_0.9` (ploidy 4.57, cellular purity 0.99, solution confidence 0.90),
its original Severus v1.7 somatic VCF, both CN BED files, and the archived
whole-genome Plotly figure. The log links these inputs explicitly.

This fuller recipe complements `hcc1954-castle-severus-wakhan`; it does not
change that recipe's data contract. The source figure supplies **57,509 50 kb
bins** of coverage and folded BAF. No BAM processing, imputation, random
sampling, or new CN inference is performed. Reference context comes from UCSC
GRCh38 cytobands and 14 selected NCBI RefSeq genes.

## View the demo

With GenomeSpy dependencies installed, build its existing browser bundle from
the **GenomeSpy root**:

```sh
npm exec --workspace @genome-spy/core -- vite build
```

From the **dataset-recipes root**:

```sh
uv run --script recipes/hcc1954-wakhan-explorer/scripts/prepare.py
uv run --script recipes/hcc1954-wakhan-explorer/scripts/serve.py
```

Open [the local demo](http://127.0.0.1:8082/specs/index.html). The server reads
GenomeSpy's bundle from the surrounding checkout. For another checkout, pass
`--genomespy /path/to/genome-spy`; `--port` changes the local port. All data and
runtime modules are local: the page needs no external requests once prepared.

The standalone [specification](specs/explorer.json) also works in the existing
GenomeSpy App dev server:

```text
http://127.0.0.1:8080/?spec=private/genomespy-dataset-recipes/recipes/hcc1954-wakhan-explorer/specs/explorer.json
```

The small HTML wrapper supplies explanatory text and six locus buttons. The
spec itself implements the tracks, brushing, tooltips, autoscaling, semantic
labels, and SV highlighting.

## Explore

- Double-click the genome navigator, then drag to draw a brush. Scroll over
  the brush to resize it; drag it to move. Scroll over
  the detail tracks to zoom and drag them to pan. Every detail track shares
  one locus viewport; the overview stays fixed and follows navigation.
- Start with **Chromosome 8**, then **HP2 CN 33** and **MYC neighbourhood**.
  MYC overlaps source CN 4 + 5; the separate CN-33 event is near 106.59 Mb.
  **ERBB2 locus** shows source CN 1 + 4, without overstating its amplification.
- Hover or click an SV arc to highlight it. A retained selection dims other
  arcs; clicking empty space clears it. BNDs require a visible endpoint at
  closer zoom; interval SVs spanning the viewport remain visible. Single
  breakends and insertions are small triangle sites, not invented arcs.
- Hover CN intervals for original start/end, haplotype, copy state, segment
  median depth, BED confidence, and breakpoint IDs. Coverage remains a
  separate point track. The paired haplotypes share a quantitative range.

This retains Wakhan's organization—SVs, haplotype depth/CN, BAF, genomic
context—but uses positive, aligned HP tracks. **HP1/HP2 are chromosome-local,
not maternal/paternal labels.** Quantitative ranges use viewport-derived
extrema, with a zero baseline and a square-root depth axis. No measured
high values are discarded or capped. Ranges settle after navigation pauses.
Genes use collision-aware labels, with only TERT, MYC, and ERBB2 labelled at
whole-genome scale. The plot is intentionally quiet until a region is explored.

## Regenerate and verify

The first preparation downloads a **5.4 GB** archive. To reuse a cached copy:

```sh
uv run --script recipes/hcc1954-wakhan-explorer/scripts/prepare.py \
  --archive /path/to/castle_benchmarks.tar.gz
uv run --script recipes/hcc1954-wakhan-explorer/scripts/prepare.py --verify-only
uv run pytest tests/test_hcc1954_wakhan_explorer.py
uv run python tools/check_repo.py
```

The standard-library Python script pins archive/member and reference-file
SHA-256s, extracts only selected members, parses literal JSON arrays without
executing Plotly HTML, and checks accepted output fingerprints. The UCSC URLs
are mutable; a changed upstream snapshot fails checksum validation instead of
silently changing the dataset. Retain the pinned download cache for long-term
reproduction. Exact sources, parameters, fingerprints, and accepted validation
are in [provenance.json](provenance.json).

**SV rule:** select the `wakhan_haplotagged` FORMAT column explicitly; require
`FILTER=PASS`, a fully called GT, and at least one allele greater than zero.
Missing/partially missing and reference genotypes are excluded regardless of
other samples. Both reciprocal BND mates must pass; otherwise preparation
fails. Their ALT coordinates must agree. Keep one representative per pair,
with both original IDs. All 1,766 records in this single-sample source pass,
producing 992 links and 82 sites. Synthetic multi-sample regression tests
exercise the exclusion rule.

Outputs in ignored `output/` are `coverage-baf.tsv`,
`copy-number-segments.tsv`, `sv-links.tsv`, `sv-sites.tsv`, `masked-regions.tsv`,
`unavailable-cn.tsv`, `cytobands.tsv`, and `genes.tsv`. Coordinates used for
plotting are zero-based, half-open. VCF anchors subtract one; original VCF
positions remain in `position1/2`. Wakhan's mixed zero/one-based first bin and
closed segment coordinates use `start=max(0,sourceStart-1)`, retaining the end.
Tooltips explicitly identify the original coordinate convention.

## Availability and limitations

- **Masked is not amplified.** The source uses `3300` as a centromeric/blacklist
  sentinel in 4,800 bins. Preserve the raw values in the table but exclude
  them from depth measurement and show 22 shaded intervals on depth/CN tracks.
  Source zero CN inside these masks is not evidence of deletion.
- Other zero depth and zero CN values remain visible as reported; an empty
  region is not filled with zeros. Sex chromosomes were outside the Wakhan
  analysis, and rounded CN terminal tails lack segments. Shading identifies
  these unavailable regions. Read coverage extends to chromosome ends.
- BAF is the source's **folded bin mean, 0–0.5**, not per-SNP data. Preserve all
  bins, including 10,900 grey zero bins. The export lacks SNP counts/depth and
  cannot distinguish unsupported zero bins from measured allelic imbalance.
- Phasing confidence and reliable genome-wide unphased depth are unavailable.
  The archived chr8 coverage figure has an all-zero `Unphased` trace; this
  alone does not establish biological absence. It is not mixed into either HP.
- All 2,116 BED segment intervals match the source figure. Copy states agree
  except for the 44 masked entries (BED zero versus HTML sentinel line values;
  HP2 tooltip state is mapped to 34). All BED
  confidence values differ from the HTML tooltip values; the BED is the
  authoritative source here. These are CN scores, not phasing confidence.
- The chosen integer CN solution is shown; no subclonal fraction is invented.
  RefSeq gene spans are unions of curated coding transcripts, not a new
  cancer-gene census or evidence that each selected gene is altered.
- Dense rearrangements still overlap at whole-genome scale; hover, selection,
  endpoint-aware filtering and zoom provide inspection. This is a single-run
  proof of concept, not a generic Wakhan importer or caller benchmark.

Local browser validation covers whole genome, chr8, CN33, MYC, ERBB2 and
chr21, synchronized scales, range coverage, brushing/panning, original-coordinate
tooltips, and console errors. See the compact results in provenance; screenshots
and detailed browser reports remain in ignored `work/`.

## Attribution and rights

Data: Ahmad Tanveer and Mikhail Kolmogorov, Wakhan / CASTLE,
[Zenodo v1](https://doi.org/10.5281/zenodo.17780982),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Cite the
[Wakhan paper](https://doi.org/10.64898/2025.12.11.25342098) and the
[Severus publication](https://doi.org/10.1038/s41587-025-02618-8).
Annotations: UCSC Genome Browser and NCBI RefSeq. Tables are transformed extracts;
no author endorsement is implied. See [RIGHTS.md](RIGHTS.md). Hosting is eligible
under its conditions; this task remains local, with no S3 upload.
