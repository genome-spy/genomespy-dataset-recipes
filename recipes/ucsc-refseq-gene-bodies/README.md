# Collapsed RefSeq gene bodies

Prepare the Python gallery's hg19/hg38 gene-body annotation table from UCSC
`refGene` snapshots. This is a Python-specific collapsed table, not a replacement
for GenomeSpy's upstream RefSeq track. No upstream example or hosted asset is
changed.

```bash
uv run --script recipes/ucsc-refseq-gene-bodies/scripts/prepare.py
uv run --script recipes/ucsc-refseq-gene-bodies/scripts/prepare.py --verify-only
```

Inputs are pinned by size and SHA-256. UCSC's URLs are mutable: a changed input
fails validation instead of silently selecting new annotations. `--source-dir`
can supply the accepted snapshots. Verification is offline.

Keep canonical chromosomes, valid strands and intervals, and nonempty symbols.
For each chromosome/strand/symbol, merge touching or overlapping transcript
intervals; count transcripts to score label priority. Coordinates stay zero-based
and half-open. Preserve group order and the hg19-then-hg38 assembly order.

The output is `refseq-gene-bodies.csv.gz`. Its decompressed CSV is identical to
the Python package's accepted table; gzip packaging differs because the recipe
omits the original filename header. The local spec shows hg19 chromosome 1.

Credit UCSC and NCBI RefSeq. See [provenance](provenance.json) and
[rights](RIGHTS.md). The repository's CC0 dedication does not license the data.

Preparation pins Python 3.14 and records the accepted runtime in provenance;
uv selects that interpreter independently of the Python wrapper environment.
