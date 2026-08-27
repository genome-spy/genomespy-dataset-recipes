# Recipe guide

## Start a recipe

Copy `recipes/_template/` and give the recipe a stable lowercase kebab-case ID.
Prefer `<subject>-<source>-<assay-or-analysis>`. Do not include `dataset`, `data`,
`demo`, `example`, `test`, `draft`, `final`, retrieval dates, parameter values,
or file formats. Add an assembly suffix only when assembly-specific variants
genuinely coexist.

Before downloading data, write down:

- the biological or technical question;
- the intended GenomeSpy example or validation use;
- candidate authoritative sources and their scale;
- assembly or other coordinate system;
- original- and derived-data redistribution evidence;
- expected outputs and scientific validation.

It is fine to keep a recipe `draft` while rights or source questions remain.
Draft outputs stay local-only.

## Directory contract

- `download/`: exact upstream inputs and large source metadata.
- `work/`: extraction, sorting, indexing, temporary, and exploratory files.
- `output/`: final local artifacts consumed by specs.
- `publish/`: optional release metadata staging, never duplicate data.
- `scripts/`: maintained preparation and validation source code.
- `specs/`: local GenomeSpy prototypes and smoke specs.

The four working directories are ignored. Scripts create them relative to their
recipe directory and must not depend on the caller's working directory.

## Maintained records

`README.md` is the primary explanation. Include sources, selection rationale,
GenomeSpy visualization rationale when genuine, coordinates, transformations,
commands, outputs, validation, limitations, rights status, and consumers.

`recipe.yaml` is a small discovery record. Keep `id`, `title`, `status`, `kind`,
sources, outputs, and consumers aligned with the README.

`RIGHTS.md` is the human-reviewed hosting decision. Record its scope,
authoritative evidence, interpretation, conditions, decision, and review date
using [the rights protocol](rights-and-publication.md). Keep `recipe.yaml` as the
matching machine-readable summary.

`sources.lock.json` identifies the pinned inputs used by ordinary runs. Prefer
immutable accessions, releases, DOI versions, or commits. Record checksums and
say whether they were verified or merely reported. If source discovery uses a
mutable query or index, pin its response identity or checksum.

`provenance.json` describes the last accepted local run: input identity,
parameters, meaningful tool versions, output checksums/counts, validation,
coordinates, and known anomalies. Keep it compact. Do not include data rows,
bulk headers, API responses, local paths, signed URLs, secrets, or incidental
timestamps.

## Python and uv

Python entrypoints use PEP 723 metadata. Scripts with third-party dependencies
also commit the adjacent uv script lock:

```bash
uv lock --script recipes/<recipe-id>/scripts/prepare.py
uv run --locked --script recipes/<recipe-id>/scripts/prepare.py
```

Use Python 3.12 or newer unless a concrete dependency requires otherwise. Use
type annotations, Ruff formatting, `pathlib.Path`, explicit encodings, context
managers, atomic writes, stable serialization/order, and fail-fast errors.

R and shell workflows are welcome when appropriate. Record meaningful runtime,
package, and external-tool versions; do not add a Python wrapper for appearance.

## Outputs and fields

Use semantic lowercase kebab-case artifact names such as
`copy-number-segments.tsv`. Preserve a stable upstream filename only for a
byte-identical mirror. Avoid names such as `data.tsv`, `new.json`, and
`output2.csv`.

Preserve standard format fields. Newly generated tabular fields use lower camel
case. Use `chrom`, `start`, and `end` for genomic intervals and document whether
coordinates are zero- or one-based and whether interval ends are included.

Write deterministic output where practical. When external tools prevent byte
identity, record stable semantic fingerprints and exact accepted tool versions.

## Validation

Validate the scientific contract, not only successful execution. Depending on
the recipe, check:

- source and output checksums;
- record counts, required fields, missingness, finite ranges, and uniqueness;
- chromosome names, coordinate bounds, origin, closure, and sorting;
- inferred companions such as `.bai`, `.tbi`, `.fai`, and `.gzi`;
- representative biological or format-specific features;
- transformations, filtering, aggregation unit, and known anomalies;
- reproducibility against the committed source lock.

## Local GenomeSpy specs

Put specs under `specs/` and load generated artifacts using
`../output/<artifact>`. Keep reusable scientific transforms in the recipe and
presentation in the spec. Specs may contain small configuration values but must
not embed source or processed dataset tables.

Recipe specs are prototypes or smoke tests. Canonical public specs remain in the
GenomeSpy repository and change only through a separate reviewed operation.

## Handoff

Before handoff:

1. Run the pinned recipe and its scientific validation.
2. Inspect applicable local specs.
3. Run `uv run python tools/check_repo.py`.
4. Run `uv run ruff check .`, `uv run ruff format --check .`,
   `uv run mypy tools recipes`, and `uv run pytest`.
5. Report reproduction commands, outputs, validation, rationale, uncertainties,
   and any remaining rights/publication work.

Publish data or edit another repository only when that work is included in the
user's request. A publication request may assess rights and upload in one
workflow; ask only when the evidence or external target remains unresolved.
