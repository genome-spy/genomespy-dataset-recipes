# TAL1 hg38 reference window

Reconstruct the reference bundle used by the Python TAL1 mutation-effect
helpers from the UCSC Genome Browser sequence API. The window was chosen for
sequence-level visualization around the example's TAL1 control site. It
contains reference bases and project-authored display metadata, not AlphaGenome
predictions, weights, or experimental measurements.

## Run

```bash
uv run --script recipes/ucsc-tal1-hg38-reference/scripts/prepare.py
```

Python 3.12 or newer is sufficient. The first run requests the exact hg38
interval, checks its assembly, coordinates, DNA length and digest, and caches
uppercase DNA. API response timestamps are deliberately excluded from the
source identity. Later runs reuse the checked cache. `--verify-only` validates
the existing output offline.

## Outputs

`output/tal1-hg38-reference.json` preserves the decoded Python bundle exactly.
The interval is zero-based, half-open; the control site's `pos1` is one-based.
The original retrieval date remains historical metadata, not a new acquisition
date. The uncompressed JSON avoids platform-dependent gzip headers and can be
loaded directly by a JSON consumer. This migration adds data preparation only;
there is no new visualization prototype.

## Validation and limitations

The recipe checks the fixed reference identity, all 131,072 bases, and the
control base after converting its coordinate. Output size and SHA-256 guard
both sequence and metadata. It does not run a prediction model or establish
any mutation's biological effect. See [provenance.json](provenance.json).

## Data rights

The [rights review](RIGHTS.md) permits hosting with source attribution. The
proposed versioned release root is recorded in provenance.
