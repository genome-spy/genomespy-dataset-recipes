# TCGA LAML combined oncoplot

Reproduce the Python combined oncoplot from six pinned maftools inputs. The
preparation runs without the Python visualization package or a sibling maftools
checkout. It leaves GenomeSpy's existing datasets and GISTIC example unchanged;
the LAML copy-number inputs are separate cohort-specific source tables.

```bash
uv run --locked --script recipes/maftools-tcga-laml-oncoplot/scripts/prepare.py
python3.14 recipes/maftools-tcga-laml-oncoplot/scripts/prepare.py --verify-only
```

Use `--source-dir PATH` for previously downloaded inputs. All six inputs are
hash-checked, including copy-number and MutSig inputs omitted from the Python
wheel. The offline verification command checks each output identity.

Outputs include unchanged mutation/clinical source tables and
`tcga-laml-combined-oncoplot.json.gz`. Every parsed table, order, annotation, and
summary matches the Python package's accepted combined bundle. The local spec
shows sample mutation-event counts from the source MAF.

Preparation preserves nonsynonymous classification and Multi_Hit handling,
12-character sample identifiers, FAB-group/mutation-based ordering, copy-number
peak joins by cytoband and boundary, pathway membership, Washington University
VAF means, MutSig q-values, and pyrimidine-normalized substitution percentages.
Burden bars count nonsynonymous variants plus genome-wide copy-number gene calls;
they are not mutations per megabase. Synonymous SNVs remain in the substitution
spectrum. Null VAF values and absent gene measurements remain null.

Credit maftools and the TCGA Research Network. See [provenance](provenance.json)
and [rights](RIGHTS.md). The repository's CC0 dedication does not license the data.

Preparation pins Python 3.14 and records the accepted runtime in provenance;
uv selects that interpreter independently of the Python wrapper environment.

Offline verification uses only the Python 3.14 standard library and requires
an already installed interpreter. The preparation command provisions its locked
third-party dependencies with uv and needs network access on a cold cache.
