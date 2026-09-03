# Data-rights review

Reviewed: 2026-09-03.

## Scope and evidence

This review covers the seven pinned members of `castle_benchmarks.tar.gz` in
[Zenodo record 17780982 v1](https://zenodo.org/records/17780982), and the UCSC
GRCh38 `cytoBandIdeo` and `ncbiRefSeqCurated` tables listed in provenance. The
outputs are eight reduced/transformed TSVs; the original Plotly HTML and
upstream program code are not repository-authored artifacts.

The Zenodo deposit by Ahmad Tanveer and Mikhail Kolmogorov identifies the
CASTLE outputs as [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
This covers the processed coverage/BAF, CN and SV extracts as adaptations.
No selected member carries a conflicting notice.

[UCSC's download policy](https://hgdownload.soe.ucsc.edu/downloads.html)
permits use for any purpose except restrictions in the relevant download
README. The [hg38 database README](https://hgdownload.soe.ucsc.edu/goldenPath/hg38/database/README.txt)
identifies GRCh38 and contains no conflicting restriction on these two tables.
The gene extract uses NCBI RefSeq, not the COSMIC annotations in Wakhan's
figure. Credit UCSC and NCBI and retain the exact source identities.

## Conditions and decision

**Eligible for GenomeSpy-managed hosting.** Credit the deposit creators and
UCSC/NCBI; link the versioned deposit, CC BY 4.0 and source tables; describe
coordinate normalization, masking, bin extraction, SV filtering and gene
selection as changes. Preserve these notices with the data and do not imply
endorsement. The repository's CC0 applies only to original scripts, specs,
and prose, never to the datasets.

The proposed release root is
`https://data.genomespy.app/datasets/hcc1954-wakhan-explorer/v1/`.
The explicit artifact inventory in provenance excludes source HTML, archives,
reference-table downloads, screenshots, and GenomeSpy runtime bundles.
