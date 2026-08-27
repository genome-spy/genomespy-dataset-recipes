---
name: develop-genomespy-example
description: Prepare or reuse a dataset and optionally prototype a local GenomeSpy specification by following this repository's recipe, provenance, rights, and no-data-in-Git conventions. Use for new dataset ideas, wrangling workflows, or recipe-local visualization prototypes; do not publish data or edit canonical GenomeSpy examples unless explicitly requested.
---

# Develop a GenomeSpy dataset example

Read `AGENTS.md`, `docs/recipe-guide.md`, and
`docs/rights-and-publication.md`. For an existing recipe, also read its
`README.md`, `provenance.json`, and `RIGHTS.md`.

Infer the requested scope: data preparation, a full local prototype, spec work
using existing output, or publication. External uploads and consumer changes
are in scope only when requested.

For a new recipe:

1. Establish the visualization idea, authoritative source, scale, assembly,
   coordinates, redistribution evidence, outputs, and scientific checks.
2. Choose a stable recipe ID and start from `recipes/_template/`.
3. Keep data in ignored working directories and use pinned inputs.
4. Provide one clear preparation workflow. Keep scientific transformations in
   scripts and presentation in specs.
5. Prototype under `specs/` with `../output/...` URLs.
6. Record concise rationale in the README, exact accepted-run details in
   `provenance.json`, and the redistribution decision in `RIGHTS.md`.
7. If hosting is eligible, record the proposed versioned URL root using
   `docs/storage-layout.md`.

Validate the recipe and spec at the requested scope. For publication, follow
the rights record, verify the hosted files, and update only the requested
consumers. Do not add deployment status to recipe metadata.
