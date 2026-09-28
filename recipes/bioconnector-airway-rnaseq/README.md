# Airway RNA-seq source tables

Acquire the exact Bioconnector workshop tables used by the Python Airway
examples: eight samples in four paired cell cultures and their rounded
kallisto/tximport length-scaled gene counts. Preserve both files byte-for-byte.
These are processed workshop counts, not raw sequencing data or DESeq2-normalized
counts. Credit Stephen Turner and UVA Bioconnector contributors, and Himes et al.,
2014, GEO GSE52778, DOI 10.1371/journal.pone.0099625.

## Preparation

```bash
uv run --locked --script recipes/bioconnector-airway-rnaseq/scripts/prepare.py
python3.14 recipes/bioconnector-airway-rnaseq/scripts/prepare.py --verify-only
```

The normal command downloads each pinned source into `download/`, checks its
identity and the paired-sample/count contract, then writes the unchanged source tables and prepared review bundle to
`output/`. Use `--source-dir PATH` for existing inputs named as in provenance.
Verification uses no network and rejects altered output files.

Outputs are `airway-metadata.csv`, `airway-scaledcounts.csv`,
`LICENSE-CC-BY-NC-SA-4.0.txt`, and the derived `airway-review.json.gz`. The local spec displays sample/condition labels.
See [provenance](provenance.json) and [rights](RIGHTS.md).
The recipe repository's CC0 dedication does not license adjacent data.

The v2 output contract adds the review bundle. Paired tests on log2(count+1)
values and BH adjustment run on the complete mean-filtered test universe before
selecting 12,000 genes for display. Labels, plot clipping, domains, sample values,
and compatibility metadata reproduce the Python workflow exactly. This is a
teaching analysis, not DESeq2. The bundle's historical source wording is preserved
for compatibility; recipe provenance records its actual inputs and preparation.

The decompressed JSON bytes match the Python package exactly. Python 3.14 writes
a different gzip OS header from the original Python 3.11 preparation, so the
compressed artifact has its own recorded hash. Locked dependency versions are
required. `scripts/review.py` is a helper, not a separate entrypoint.

Preparation pins Python 3.14 and records the accepted runtime in provenance;
uv selects that interpreter independently of the Python wrapper environment.

Offline verification uses only the Python 3.14 standard library and requires
an already installed interpreter. The preparation command provisions its locked
third-party dependencies with uv and needs network access on a cold cache.
