# UniProt P53 protein alignment

Align the 34 historical UniProt P53 sequences selected by Plotly's Dash Bio
fixture. This set supports the Python gallery's residue matrix, conservation
tracks, sequence logo, and linked alignment-column navigation. The fixed
selection preserves the existing example rather than introducing a new cohort.

## Run

Install MAFFT 7.526 and Python 3.12 or newer, then run:

```bash
uv run --script recipes/uniprot-p53-alignment/scripts/prepare.py
```

Use `--mafft /path/to/mafft-linsi` for an isolated installation. The pinned
[MAFFT source revision](https://gitlab.com/sysimm/mafft/-/tree/ee9799916df6a5d5103d46d54933f8eb6d28e244)
can be built with `make` and `make install` in `core/`, setting `PREFIX` to a
local installation directory for both commands.

The workflow downloads the pinned Plotly FASTA, verifies it, and invokes
`mafft-linsi` without extra arguments, preserving the historical non-threaded
L-INS-i invocation. Do not substitute `--thread 1`: that path produces a
different alignment. The output digest rejects such changes. `--verify-only`
checks an existing output without downloading or invoking MAFFT.

## Outputs

`output/p53-aligned.fasta` exactly matches the decompressed packaged alignment,
including sequence order, full headers, gap placement, and line wrapping.
`output/PLOTLY-LICENSE.txt` preserves the pinned contributor notice and must
accompany the alignment.
FASTA is uncompressed to avoid platform-dependent gzip headers. Headers retain
UniProt accessions and sequence versions, including mouse P02340 version 3.
This migration adds data preparation only; the Python gallery remains the
visualization reference and no new prototype is introduced.

## Validation and limitations

Preparation requires a rectangular 34-sequence alignment, unchanged ungapped
residues and headers, and exact output size and SHA-256. This historical teaching
selection is not a systematic phylogenetic sample. Alignment gaps must not be
interpreted as experimentally observed deletions. Exact source and output
identities are in [provenance.json](provenance.json).

## Data rights

The [rights review](RIGHTS.md) permits hosting under CC BY 4.0 with attribution
and a modification notice. The proposed release root is recorded in provenance.
