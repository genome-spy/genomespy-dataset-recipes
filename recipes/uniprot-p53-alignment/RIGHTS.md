# Data-rights review

## Scope

The 34 UniProt protein sequences in the pinned Plotly FASTA, transformed by
MAFFT L-INS-i into an aligned FASTA. No MAFFT or Plotly software is redistributed
by this recipe.

## Evidence and interpretation

[UniProt's license](https://www.uniprot.org/help/license/), also available from
[its REST service](https://rest.uniprot.org/help/license), applies CC BY 4.0
to copyrightable database content. Accessions and sequence versions identify
the inputs. Mouse P02340 uses historical sequence version 3, retained in
[UniSave entry 231](https://rest.uniprot.org/unisave/P02340?format=txt&versions=231).
The existing Python source audit established that all 34 ungapped sequences
match the identified UniProt records. MAFFT's software license does not license
its output. The recipe code is original orchestration, not copied MAFFT code.

## Conditions

Credit the UniProt Consortium and Plotly's selection/formatting of the teaching
fixture; link the source and [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Retain accession/version headers and disclose the MAFFT alignment. Publish `PLOTLY-LICENSE.txt` alongside the alignment to preserve
Plotly's contributor notice for any copyrightable selection/formatting. UniProt
disclaims correctness and does not grant patent or other third-party rights.
The recipe's CC0 dedication does not license the sequences.

## Decision

Eligible for GenomeSpy-managed hosting under the conditions above.

Reviewed: 2026-10-09
