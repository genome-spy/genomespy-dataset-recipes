# Single-sample TCGA BRCA mutations

Acquire the maftools mutation table used by the Python rainfall example without
changing its compressed bytes. The table contains 1,913 SNVs from the single
sample TCGA-A8-A08B; it is not a cohort-wide BRCA mutation dataset. It is useful
for illustrating mutation positions and distances between neighboring events.

## Run

```bash
uv run --script recipes/maftools-tcga-brca-mutations/scripts/prepare.py
python3 recipes/maftools-tcga-brca-mutations/scripts/prepare.py --verify-only
```

Use an installed Python 3.12+ interpreter for dependency-free offline
verification. Preparation downloads the pinned source or accepts cached inputs
with `--source-dir PATH`. Changed inputs fail the size/SHA-256 checks.

## Output and prototype

`output/brca.maf.gz` preserves the nine-column source MAF exactly. Positions are
one-based and inclusive. The source omits an assembly field; this recipe does
not infer an assembly or convert coordinates. Its local spec plots SNV counts
by chromosome without a genome coordinate scale. Chromosomes retain their source
names and are shown in numerical order followed by X.

Validation checks the sample, columns, row count, chromosome set, SNV alleles,
and positive single-base intervals. The Python rainfall helper still derives
intermutation distances and annotations; these are not additional recipe outputs.

Credit Anand Mayakonda/maftools and the TCGA Research Network. See
[provenance](provenance.json) and [rights](RIGHTS.md). Managed hosting remains
unresolved; the recipe currently supports reproducible local acquisition only.
