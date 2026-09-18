# Mouse fetal-development H3K27ac and expression (mm10)

This recipe creates a compact GenomeSpy App demonstration of tissue-specific
regulatory activity during mouse fetal development. It keeps individual
H3K27ac biological replicates for forebrain, heart, and limb at E11.5, E12.5,
E13.5, and E15.5, then adds bulk RNA-seq tissue-stage means as metadata.

The assays are condition-matched, not sample-paired. Every expression value is
the mean of two RNA biological replicates and is intentionally repeated for
both H3K27ac rows with the same tissue and embryonic age. The tissue samples
are dissected embryonic tissue pools, not longitudinal measurements from
individual mice.

## Why this dataset

Gorkin et al. produced a mouse fetal chromatin atlas and validated candidate
enhancers with transgenic reporter assays. He et al. profiled bulk RNA from the
same tissue-stage resource. Together they support a concise visual story in
which H3K27ac contrasts are visible in the signal tracks and expression helps
identify tissue state rather than carrying the narrative by itself.

Phase 1 tested six E12.5 H3K27ac tracks at a shared linear scale. The viewer can
identify the intended tissue from the tracks at all four retained examples:

- five replicated enhancer-gene predictions in the Ascl1 neighbourhood are
  forebrain-associated;
- mEN886/mm1606 is forebrain-associated;
- mEN978/mm1683 is heart-associated;
- mEN918/mm1617 is limb-associated.

mEN917/mm1616 was rejected because heart and limb were similarly strong.
mEN976/mm1681 and mEN916/mm1615 were also rejected in favour of clearer
contrasts. `output/candidate-assessment.tsv` records the decisions and the
E12.5 replicate summaries. This was a bounded check of published candidates,
not a genome-wide enhancer search.

## Retained regions and size

The source H3K27ac files total 16,616,455,932 bytes (about 15.5 GiB). The
recipe uses remote range reads and writes native intervals and values only
inside the same four regions for all 24 rows. The broad Ascl1 landscape is the
initial exploration view; the other three windows remain compact:

| Region | Zero-based, half-open bounds | Purpose |
| --- | --- | --- |
| Ascl1 landscape | `chr10:82,400,000-92,400,000` | Ten-megabase overview containing the focused Ascl1 neighbourhood and five retained predictions |
| mEN886 | `chr12:111,200,000-112,200,000` | Forebrain reporter element and overlapping Ckb prediction |
| mEN978 | `chr7:139,000,000-140,000,000` | Heart reporter element |
| mEN918 | `chr9:42,750,000-43,750,000` | Limb reporter element |

The resulting regional BigWigs total 111,314,653 bytes (about 106.2 MiB). The
included-region track labels the available interval on each chromosome and is
searchable by region name. Users can pan and zoom throughout the ten-megabase
initial view or within the three focused one-megabase windows. Absence of
signal outside these windows means that no data were retained there, not that
the locus is inactive.

## Accepted samples

The panel contains 24 H3K27ac rows: two biological replicates for each of 12
tissue-stage conditions. Each row uses one released mm10 ENCODE `fold change
over control` BigWig from the Histone ChIP-seq 2 (unreplicated) pipeline. The
accepted RNA panel contains 24 released GENCODE M21 gene-quantification tables,
also two biological replicates per tissue-stage.

| Tissue | Stages | H3K27ac rows | RNA files |
| --- | --- | ---: | ---: |
| Forebrain | E11.5, E12.5, E13.5, E15.5 | 8 | 8 |
| Heart | E11.5, E12.5, E13.5, E15.5 | 8 | 8 |
| Limb | E11.5, E12.5, E13.5, E15.5 | 8 | 8 |

`output/selection-report.tsv` gives the exact experiment, file, tissue, stage,
replicate, and source-file size. `provenance.json` pins the accepted manifest,
so routine preparation does not repeat an open-ended portal search.

Sample rows use compact, unique labels such as `Forebrain E12.5 R1`. They remain
self-identifying when grouping is removed, while the App determines the label
column width automatically.

ENCODE audits include historical metadata and pipeline warnings involving
library complexity, bottlenecking, read depth or length, controls, and
platforms. The E12.5 heart experiment ENCSR123MLY also has NOT_COMPLIANT
library-complexity and bottlenecking entries. These tracks were retained
because their biological replicates agree at the curated loci and the atlas
used the experiment, but the caveat is explicit and the tracks must not be
treated as absolute acetylation measurements across tissues.

## Expression metadata

For each tissue-stage and selected gene, the recipe retains both individual
RNA TPM measurements and computes the condition mean, its log transform, and a
gene-wise z-score:

```text
z = (log2(mean TPM across the two RNA replicates + 1) - gene mean) / gene SD
```

The mean and standard deviation are calculated separately for each gene across
the 12 tissue-stage conditions. Thus, zero is that gene's panel mean and the
default diverging heatmap emphasizes relative expression within this selected
panel; z-scores are not absolute expression and should not be compared between
genes as abundance measurements. Raw mean TPM and `log2(mean TPM + 1)` remain
available as initially hidden metadata. Missing values would remain missing;
the preparation code never imputes zero or interpolates conditions.

The eight columns are Ascl1, Ckb, Foxg1, Tnnt2, Nkx2-5, Hand2, Prrx1, and Myog.
Ascl1 is part of the retained neighbourhood; Ckb is the both-replicate
predicted target of the enhancer interval overlapping mEN886. The remaining
genes provide documented forebrain, heart, limb, and myogenic identity context.
Reporter-tested mEN978 and mEN918 are not assigned endogenous target genes.

## Run

Python 3.12 or newer and `uv` are required. Preparation downloads about 285 MiB
of pinned RNA quantification tables plus the pinned GENCODE M21 annotation and
two source workbooks. It does not download the genome-wide BigWigs.

```bash
uv run --locked --script \
  recipes/encode-mouse-fetal-development-mm10/scripts/prepare.py
```

Validate the existing local inputs and outputs without network access:

```bash
uv run --locked --script \
  recipes/encode-mouse-fetal-development-mm10/scripts/prepare.py \
  --verify-only
```

## Outputs and local App prototype

- `output/bigwigs/<sampleId>.bigWig`: 24 full-resolution regional extracts.
- `output/samples.tsv`: H3K27ac row identity, provenance, and condition-level
  expression metadata. Dotted column names form Sample, H3K27ac, and RNA-seq
  groups in the App.
- `output/expression-conditions.tsv`: 96 tissue-stage-gene summaries.
- `output/expression-replicates.tsv`: 192 individual RNA measurements.
- `output/regions.tsv`: the four searchable retained regions.
- `output/elements.tsv`: published reporter and prediction intervals with
  evidence types kept distinct. The preparation script extracts these rows from
  the pinned Gorkin workbook using the selection rules in `provenance.json`.
- `output/genes.tsv`: GENCODE M21 genes overlapping the retained regions.
- `output/candidate-assessment.tsv`: accepted and rejected feasibility loci.
- `output/selection-report.tsv`: exact accepted H3K27ac and RNA sources.
- [`specs/spec.json`](specs/spec.json): the root GenomeSpy App prototype;
  imported files in the same directory define individual annotation tracks,
  the sample collection, metadata, and H3K27ac signal.
- [`specs/bookmarks.json`](specs/bookmarks.json): the six-stop tour.

From a GenomeSpy checkout with the App running at port 8080, open:

```text
http://localhost:8080/?spec=private/genomespy-dataset-recipes/recipes/encode-mouse-fetal-development-mm10/specs/spec.json
```

The first bookmark introduces the complete 24-row panel, the annotation tracks,
and the expression transformation. The H3K27ac scale starts at zero, is shared
across displayed rows, and adapts to the current viewport and visible samples.
The second compares tissues at the *Ascl1* predictions at E12.5. The third uses
a genomic brush to derive weighted-mean H3K27ac for the selected interval and
opens a scatter plot against *Ascl1* expression. The fourth and fifth show the
E12.5 heart and limb reporter examples. The sixth keeps all 24 rows, groups
tissue → stage, and sorts by replicate at mEN886. Source table rows are ordered
tissue → chronological stage → biological replicate, which is the default
full-panel order.

## Interpretation and limitations

The visualization is a curated four-region example, not a genome-wide atlas.
It does not perform differential analysis, discover enhancers, infer new
enhancer-gene links, or establish causal regulation. H3K27ac enrichment,
reporter activity, computational enhancer-gene predictions, and gene expression
are displayed as separate evidence types. Reporter activity does not prove an
endogenous target, and correlated H3K27ac and RNA do not prove causality.

The regions preserve source resolution but not genome-wide coverage. The shared
H3K27ac scale supports comparison among the rows visible in one viewport, but
its domain changes after zooming, panning, or filtering samples. The processed
signals still should not be interpreted as calibrated absolute acetylation
abundance between tissues. Limb follows the source atlas label and refers to a
pooled dissected embryonic limb preparation rather than separate forelimb and
hindlimb conditions.

## Data rights

The [rights review](RIGHTS.md) finds the exact regional ENCODE derivatives and
compact annotation tables eligible for GenomeSpy-managed hosting with ENCODE,
GENCODE, and article attribution. No upload or publication is performed by
this recipe change.

Proposed release root:
`https://data.genomespy.app/datasets/encode-mouse-fetal-development-mm10/v4/`.
