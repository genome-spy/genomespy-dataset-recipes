# Data-rights review

Reviewed: 2026-09-15.

## Scope and evidence

This review covers the eight pinned members of `castle_benchmarks.tar.gz` in
[Zenodo record 17780982 v1](https://zenodo.org/records/17780982), and the UCSC
GRCh38 `cytoBandIdeo` and `ncbiRefSeqCurated` tables and NCG 7.2 cancer-driver
evidence table listed in provenance. The outputs are nine reduced/transformed
TSVs; the original Plotly HTML and upstream program code are not
repository-authored artifacts.

The Zenodo deposit by Ahmad Tanveer and Mikhail Kolmogorov identifies the
CASTLE outputs as [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
This covers the processed coverage/BAF, CN and SV extracts as adaptations.
No selected member carries a conflicting notice.

[UCSC's download policy](https://hgdownload.soe.ucsc.edu/downloads.html)
permits use for any purpose except restrictions in the relevant download
README. The [hg38 database README](https://hgdownload.soe.ucsc.edu/goldenPath/hg38/database/README.txt)
identifies GRCh38 and contains no conflicting restriction on these two tables.
The [NCG publication](https://doi.org/10.1186/s13059-022-02607-z) states that
the complete database can be freely downloaded and requires no license. Its
download page requests citation of the latest publication. The gene extract
uses its canonical-driver classification and supporting PubMed identifiers,
with coordinates from NCBI RefSeq; it does not use the COSMIC annotations in
Wakhan's figure. Credit NCG, UCSC, and NCBI and retain the exact source
identities.

## Decision

Eligible for GenomeSpy-managed hosting under the conditions above. Credit the
deposit creators, NCG, UCSC, and NCBI; link the versioned deposit, CC BY 4.0 and
source tables; describe
coordinate normalization, masking, bin extraction, SV filtering, gene mapping,
and evidence aggregation as changes. Cite the NCG publication. Preserve these
notices with the data and do not imply endorsement. The repository's CC0 applies
only to original scripts, specs, and prose, never to the datasets.

The proposed release root is
`https://data.genomespy.app/datasets/hcc1954-wakhan-explorer/v5/`.
The explicit artifact inventory in provenance excludes source HTML, archives,
reference-table downloads, screenshots, and GenomeSpy runtime bundles.
