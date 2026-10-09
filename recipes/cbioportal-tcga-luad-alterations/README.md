# Historical TCGA LUAD alteration export

Preserve the pyoncoprint cBioPortal LUAD PanCancer Atlas 2018 export used by
the Python oncoprint example. The wide table contains 145 tracks and 507 sample
columns, combining alteration, clinical, expression, and generic-assay tracks.
It provides the existing oncoprint's varied track types and missing-value cases.

> **Historical data warning:** Dicipivirus values come from Poore et al. (2020),
> [retracted in 2024](https://doi.org/10.1038/s41586-024-07656-x).
> cBioPortal [removed the profile](https://github.com/cBioPortal/datahub/commit/18edd66a52b4d1b10a697e8d2fee79e1b1452b73)
> on 2024-07-08. These values are preserved for fixture compatibility and must
> not be presented as validated biological findings.

## Run

```bash
uv run --script recipes/cbioportal-tcga-luad-alterations/scripts/prepare.py
python3 recipes/cbioportal-tcga-luad-alterations/scripts/prepare.py --verify-only
```

The offline verification command requires an installed Python 3.12+ interpreter.
Preparation downloads a commit-pinned input and verifies size and SHA-256 before
writing it. `--source-dir PATH` accepts a previously downloaded `tcga.tsv`.
A changed cache fails rather than silently fetching a replacement.

## Output and validation

`output/tcga.tsv` is byte-identical to the Python package's source table.
Column order, empty cells, numeric strings, clinical text, and historical tracks
remain unchanged. No coordinates or reference assembly are inferred.
Checks cover dimensions, unique sample columns, unique track-name/type pairs,
track-type counts, and the historical microbiome track's presence.

The prototype shows the number of source tracks of each type. These are table
structure counts, not patient alteration frequencies or biological evidence.
The Python helper still reshapes the table and ranks genes/samples for the full
oncoprint; those derived tables are not new outputs of this acquisition recipe.

Credit TCGA, cBioPortal, the contributing studies, and pyoncoprint.
See [provenance](provenance.json) and [rights](RIGHTS.md). Managed hosting is
unresolved; the recipe currently supports reproducible local acquisition.
