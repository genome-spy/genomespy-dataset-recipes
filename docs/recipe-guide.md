# Recipe guide

## Start with the example

Before writing a pipeline, identify the intended visualization, assembly or
coordinate system, authoritative source, likely output size, and redistribution
terms. Prefer data that exercise a useful GenomeSpy capability without being
larger or more sensitive than the example needs.

Copy `recipes/_template/` and choose a lowercase kebab-case ID. A useful pattern
is `<source>-<subject>-<assay-or-analysis>`. Omit generic words such as `data`,
`dataset`, `example`, `test`, `draft`, and `final`; omit dates and file formats.
Add an assembly only when it disambiguates the biological meaning or variants
may coexist.

## Directory and record contract

```text
recipes/<recipe-id>/
├── README.md
├── RIGHTS.md
├── provenance.json
├── scripts/
├── specs/
├── download/   # ignored inputs
├── work/       # ignored intermediates
└── output/     # ignored artifacts loaded by specs
```

`README.md` answers why the dataset was chosen, why it helps demonstrate
GenomeSpy, how to run the recipe, what it produces, and what its limitations
are. Avoid checksums, exhaustive statistics, release state, and repeated policy
text; link to the other two records.

`provenance.json` is the compact machine-readable record for the last accepted
run. It contains:

- `schemaVersion`, `recipeId`, and `releaseId`;
- exact `sources`, including stable URLs or accessions and checksums;
- parameters and transformations that affect scientific meaning;
- meaningful tool versions;
- output paths, checksums, sizes or record counts as useful;
- validation results and known anomalies.

Do not include data rows, bulk headers, local absolute paths, signed URLs,
secrets, timestamps with no reproducibility value, or deployment status.

`schemaVersion` identifies the shape of the provenance record. `releaseId`
identifies the accepted dataset and output contract and starts at `v1`.
Increment it for a change to accepted output bytes, scientific meaning,
included samples, rows or columns, field definitions, filenames, companion
files, or output layout. Do not increment it for documentation, rights
evidence, validation commentary, or an implementation refactor that reproduces
the accepted outputs exactly.

Schema version 2 adds the explicit `distribution.artifacts` publication
inventory. Migrating an unchanged accepted output from schema version 1 to 2
does not increment `releaseId`.

`RIGHTS.md` records the evidence and decision for redistribution. Keep it about
eligibility and conditions, not whether an object currently exists on S3.
When hosting is eligible, add the proposed versioned release root as
`distribution.baseUrl` in provenance, following the
[hosted data layout](storage-layout.md). Its version segment must equal
`releaseId`. Add every public artifact to `distribution.artifacts` with its
path relative to the recipe, byte size, and SHA-256. This is an explicit
publication allowlist, not deployment state.

## Scripts and uv

Provide one obvious preparation command when practical. Scripts resolve paths
from their own location, create working directories as needed, pin ordinary
runs, and fail rather than silently accepting changed input.

Python entrypoints use PEP 723 metadata:

```bash
uv run --script recipes/<recipe-id>/scripts/prepare.py
# When third-party dependencies are listed:
uv lock --script recipes/<recipe-id>/scripts/prepare.py
uv run --locked --script recipes/<recipe-id>/scripts/prepare.py
```

Use Python 3.12 or newer unless a dependency requires otherwise. Favor type
annotations, `pathlib.Path`, explicit encodings, context managers, stable
sorting and serialization, atomic writes, and focused functions. R and shell
are equally acceptable when they express the scientific workflow more clearly.

## Outputs and specs

Name generated artifacts by content: `copy-number-segments.tsv.gz`, not
`data.tsv` or `output2.csv`. Preserve standard-format names and extensions.
New tabular fields use lower camel case; genomic intervals use `chrom`, `start`,
and `end` unless an established format dictates otherwise. Document coordinate
origin and interval closure.

Specs belong in `specs/` and load local results with
`../output/<artifact>`. Keep scientific shaping in scripts and presentation in
the spec. Do not embed dataset tables in specs.

## Validation and handoff

Validate the scientific contract: input identity, output fingerprints, required
fields, coordinates, sorting, ranges, companion indexes, and representative
features needed by the visualization. Record useful summaries in provenance,
not a transcript of every check.

Before handoff, run the documented preparation or verification command, inspect
the relevant specs, and run the repository checks. Publish data or edit another
repository only when requested.
