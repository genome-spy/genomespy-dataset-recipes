# Data-rights review

## Scope

The input is the authors' `zenodo-bpreveal-files.tar.bz2` archive from Zenodo
record 20318019. The recipe extracts the derived PISA HDF5 matrix, predicted
and importance BigWigs, motif BED file, and PISA-input FASTA for the shared
Figure 2c/2d locus. Its outputs are small locus-specific Parquet
transformations, including reference bases derived from that FASTA.

## Evidence and interpretation

- Paper: <https://doi.org/10.1038/s41467-026-74807-1>
- Zenodo record: <https://zenodo.org/records/20318019>
- Zenodo license guidance:
  <https://help.zenodo.org/docs/deposit/describe-records/licenses/>
- Stowers publication record: <https://www.stowers.org/research/publications/libpb-2546>

The authors' Zenodo record identifies the resource as a dataset and assigns the
entire deposit the GNU General Public License v2.0 or later
(`GPL-2.0-or-later`). Zenodo describes its required license field as the terms
under which users may reuse an upload and provides separate handling for mixed
license deposits. The record declares only `GPL-2.0-or-later`.

The selected HDF5, BigWig, BED, and FASTA members are author-deposited PISA
results, model predictions, importance scores, motif calls, and model-input
reference sequence rather than copies of the underlying sequencing reads. The
Parquet files are reduced and reformatted derivatives of those licensed files.
Although GPL is unusual for data, its permission to modify and redistribute
the licensed work covers these extracts.

## Conditions

- Distribute the Parquet extracts under `GPL-2.0-or-later`, retain the license
  notice, and impose no additional restrictions on recipients.
- State prominently that GenomeSpy selected, transformed, and reformatted the
  data on 2026-09-22; do not present the extracts as the original deposit.
- Retain the no-warranty notice and provide a copy of, or link to, the
  [GPL v2 license](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).
- Credit McAnany et al.; cite the paper and Zenodo record 20318019. Also retain
  the paper's identification of GSE218852 as the training data source for the
  accessibility model.
- State that the recipe repository's CC0 dedication does not cover the data.

## Decision

Eligible for GenomeSpy-managed hosting under the conditions above.

The four Parquet outputs listed in `provenance.json` may be hosted. The
unmodified Zenodo archive and extracted HDF5, BigWig, BED, and FASTA
intermediates are outside this publication decision.

Reviewed: 2026-09-23
