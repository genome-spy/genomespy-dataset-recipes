# Synthetic mutation-impact reference

Preserve the tiny authored reference window used by the Python project's Marimo
mutation-impact prototype. Its 20 fictional bases and periodic scores are useful
for demonstrating position, base color, and score encodings without a biological
source dataset. `synthetic-v1` and `chrSynthetic` are fictional identifiers.

## Run

```bash
uv run --script recipes/synthetic-mutation-impact/scripts/prepare.py
python3 recipes/synthetic-mutation-impact/scripts/prepare.py --verify-only
```

Preparation acquires a pinned public Python-project fixture and MIT notice,
verifies both hashes, and checks all coordinates, bases, and scores before
preserving their bytes. `--source-dir PATH` accepts verified cached inputs.
Verification needs only an installed Python 3.12+ interpreter and no network.

## Outputs and interpretation

`output/mutation-impact-reference.json` preserves the existing metadata and
`rows` array. Positions are zero-based consecutive coordinates in the fictional
reference. For row index i, the score is `(5 + (3*i mod 11)) / 20`.
The fixed base sequence is authored input, not generated biological sequence;
this recipe validates and reproduces the accepted fixture's acquisition.
Scores are teaching values, not mutation effects, probabilities, or predictions.

`specs/overview.json` shows the score at each fictional position, colored by base.
See [provenance](provenance.json) for accepted identities and parameters, and
[rights](RIGHTS.md) for the MIT attribution conditions. The proposed release
root is recorded in provenance. Publish `LICENSE-MIT.txt` with the JSON.
