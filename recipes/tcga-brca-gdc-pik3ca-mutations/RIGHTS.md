# Data-rights review

## Scope

This review covers the exact 992 open TCGA-BRCA GDC masked somatic MAFs and
UniProtKB reviewed human PIK3CA entry P42336 identified in `provenance.json`.
The proposed outputs are:

- `mutations.tsv`, a small aggregation that selects one gene and transcript,
  excludes non-protein-altering and singleton events, removes genomic loci and
  sample identifiers, and reports distinct tumour-sample counts; and
- `domains.tsv`, a five-row extract of selected P42336 domain annotations.

Neither output is an unchanged mirror of an input.

## Evidence and interpretation

The authoritative [GDC MAF format documentation](https://docs.gdc.cancer.gov/Data/File_Formats/MAF_Format/)
distinguishes protected MAFs from somatic, open-access MAFs. It states that
somatic MAFs are publicly available and may be freely distributed within the
GDC Data Access Policies, and explains that potentially identifying germline
information is filtered or blanked. Every accepted GDC input is recorded as
`access: open` and has the masked somatic filename and workflow identity.

The NCI [TCGA citation guidance](https://www.cancer.gov/ccg/research/genome-sequencing/tcga/using-tcga-data/citing)
requests acknowledgment of the TCGA Research Network for uses of TCGA data and
states that all disease-specific publication moratoria have been lifted.

The authoritative [UniProt license page](https://www.uniprot.org/help/license/)
applies CC BY 4.0 to copyrightable parts of UniProt databases. It also warns
that some content can be affected by patents or other rights and disclaims
medical use. The output uses only five factual domain intervals and labels from
one reviewed entry; no third-party cross-reference content is copied.

Together, those terms permit redistribution of the transformed mutation table
and the attributed domain extract. The processing does not relax the upstream
conditions and does not imply that patient-derived facts or UniProt data become
CC0.

## Conditions

- Identify GDC TCGA-BRCA open masked somatic MAFs as the mutation source and
  acknowledge the TCGA Research Network.
- Link to the GDC project or documentation and do not describe the masked MAFs
  as complete somatic callsets.
- Attribute UniProt Consortium entry P42336, link to CC BY 4.0, and identify
  `domains.tsv` as a selected and reformatted extract.
- Do not imply endorsement or suitability for diagnosis, treatment, or other
  clinical use.
- Do not imply that the recipe repository's CC0 dedication covers either data
  output.

## Decision

Eligible for GenomeSpy-managed hosting under the conditions above.

Reviewed: 2026-08-27
