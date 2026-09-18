# Data-rights review

## Scope

This review covers the MCCA-derived sample, model-allele, copy-ratio, mutation,
and expression artifacts recorded in `provenance.json`; the derived sequencing
availability table from public ENA run metadata; the derived GENCODE M25 gene
track scored with NCBI Gene mapping and PubMed-link counts; and the unchanged
UCSC mm10 `cytoBandIdeo` table.

The repository redistributes prepared artifacts, not the source workbooks,
transcriptome archive, GENCODE GTF, or NCBI bulk tables. The repository's CC0
dedication applies to the original workflow and specs, never to input or output
data.

## Evidence and interpretation

On June 26, 2026, corresponding author Ronald Rad wrote by email to Kari
Lavikka, in response to a question about the unclear data-use policy: “the data
are of course publicly available to use for everyone”. The private email is not
committed to this repository. Its sender, context, date, and explicit statement
support public use and redistribution of the exact MCCA-derived artifacts in
this recipe with source attribution and without implying author endorsement.

The MCCA resource is described by Mueller et al., DOI
[`10.1038/s41586-026-10187-2`](https://doi.org/10.1038/s41586-026-10187-2).

The [EMBL-EBI terms of use](https://www.ebi.ac.uk/about/terms-of-use/) state
that EMBL-EBI imposes no additional restriction on contributed scientific data
beyond the data owner's terms and expects attribution. The recipe uses public
ENA run metadata only to report assay availability for PRJEB105230 and
PRJEB105231.

The GENCODE [data-access page](https://www.gencodegenes.org/pages/data_access.html)
states that all GENCODE project data are open access. The recipe redistributes
a transformed gene-model track from the pinned mouse M25 GTF and identifies the
release and transformation.

The NCBI [copyright and disclaimer policy](https://www.ncbi.nlm.nih.gov/About/disclaimer.html)
state that NCBI places no restrictions on use or distribution of its molecular
data, while noting that third-party submitters may retain rights. This recipe
uses mouse gene-to-Ensembl mappings and factual PubMed identifier counts only,
and acknowledges NCBI/NLM.

The UCSC Genome Browser [licensing page](https://genome.ucsc.edu/license/)
states that its downloadable raw table data are freely available for public and
commercial use, subject to any track-specific source restriction. The mm10
`cytoBandIdeo` table is published on the UCSC download server without an
additional restriction identified for that table. The recipe preserves it
byte-for-byte and credits UCSC.

## Conditions

- Cite Mueller et al. and identify MCCA as the source of the cell-line data.
- Identify the visualization as an independent GenomeSpy demo and do not imply
  endorsement by the publication authors.
- Credit ENA/EMBL-EBI and identify PRJEB105230 and PRJEB105231 when presenting
  sequencing availability.
- Identify GENCODE mouse M25, NCBI Gene/PubMed mappings, and the UCSC mm10
  `cytoBandIdeo` table for the supporting annotation artifacts.
- Preserve the NCBI/NLM and UCSC acknowledgments and applicable disclaimers.
- Do not imply that the repository's CC0 dedication licenses dataset artifacts.

## Decision

Eligible for GenomeSpy-managed hosting under the conditions above. This
decision applies only to the exact `v1` artifacts identified in
`provenance.json`.

Reviewed: 2026-09-18
