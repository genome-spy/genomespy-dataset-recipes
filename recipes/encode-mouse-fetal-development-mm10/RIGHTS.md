# Data-rights review

## Scope

This review covers 24 regional BigWigs derived from released ENCODE H3K27ac
signals; compact tables derived from released ENCODE metadata and bulk RNA-seq
gene quantifications; GENCODE M21 gene records overlapping four retained
regions; and nine literature-derived reporter or enhancer-prediction annotation
rows. Exact source files and generated artifact identities are recorded in
`provenance.json`.

The GENCODE GTF and Gorkin et al. workbooks are reproducibility inputs. The
recipe redistributes only small factual subsets required for the prototype, not
the source files. The articles are scientific context; no figures or article
text are copied into the outputs.

## Evidence and interpretation

ENCODE's authoritative
[data-use policy](https://www.encodeproject.org/about/data-use-policy/) states
that released ENCODE data are available for unrestricted use immediately upon
release. Its [citation guidance](https://www.encodeproject.org/help/citing-encode/)
permits download, analysis, and publication while asking users to credit the
ENCODE Consortium and producing laboratory and identify contributing
experiments and files. Every accepted file is released. The manifest records
the Bing Ren laboratory H3K27ac and Barbara Wold laboratory RNA contributions,
along with all `ENCSR...` and `ENCFF...` accessions.

The BigWigs are newly written regional derivatives that retain source intervals
and values only within four declared mm10 windows. The expression tables contain
factual source identifiers and newly computed tissue-stage means and gene-wise
z-scores. ENCODE's
unrestricted-use policy supports redistribution with the attribution conditions
below.

GENCODE's authoritative
[data-access page](https://www.gencodegenes.org/pages/data_access.html) states
that all GENCODE project data are open access. The recipe redistributes only
307 gene records overlapping the retained windows, with coordinates converted
from GTF one-based inclusive to zero-based half-open, and identifies M21 as
the annotation release.

Gorkin et al., DOI
[`10.1038/s41586-020-2093-3`](https://doi.org/10.1038/s41586-020-2093-3),
and its supplementary materials are published under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The CaltechAUTHORS
[record](https://authors.library.caltech.edu/records/bbq8c-fbs42) states the
license and provides the source workbooks. `elements.tsv` adapts a small factual
subset of Supplementary Tables 8c and 10: coordinates, identifiers, reported
prediction support, and reporter counts. The recipe and bookmark text identify
the source, preserve the evidence distinctions, and indicate that the
annotations were selected and reformatted.

He et al., DOI
[`10.1038/s41586-020-2536-x`](https://doi.org/10.1038/s41586-020-2536-x),
is also published under CC BY 4.0. It supplies scientific context for the
companion bulk tissue expression resource. The redistributed measurements are
derived from the released ENCODE files rather than copied from article figures
or prose.

## Conditions

- Credit the ENCODE Consortium, the Bing Ren laboratory for H3K27ac, and the
  Barbara Wold laboratory for RNA-seq.
- Identify the contributing ENCODE experiments and files; the generated
  selection report is the compact accession list.
- Cite Gorkin et al. for the chromatin atlas, reporter results, and
  enhancer-gene predictions, and state that those annotation rows were selected
  and reformatted under CC BY 4.0.
- Cite He et al. when presenting the bulk tissue expression context.
- Identify GENCODE M21 and its open-access source for redistributed gene records.
- Describe the BigWigs as GenomeSpy-produced regional derivatives, not unchanged
  ENCODE files or whole-genome tracks.
- Describe expression fields as GenomeSpy-produced tissue-stage summaries of
  released ENCODE quantifications.
- Do not imply that repository CC0 covers dataset artifacts or that ENCODE,
  GENCODE, the producing laboratories, or the cited authors endorse the mirror.

## Decision

Eligible for GenomeSpy-managed hosting under the conditions above. This
decision applies only to the exact `v4` artifacts recorded in
`provenance.json`; publication and upload remain out of scope for this work.

Reviewed: 2026-09-18
