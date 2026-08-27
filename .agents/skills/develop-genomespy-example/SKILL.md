---
name: develop-genomespy-example
description: Prepare or reuse a dataset and optionally prototype a local GenomeSpy specification by following this repository's recipe, provenance, rights, and no-data-in-Git conventions. Use for new dataset ideas, wrangling workflows, or recipe-local visualization prototypes; do not use for publishing data or editing canonical GenomeSpy examples unless explicitly requested.
---

# Develop a GenomeSpy dataset example

Read the repository `AGENTS.md`, `docs/recipe-guide.md`,
`docs/rights-and-publication.md`, and the target recipe README and `RIGHTS.md`
before acting.

Infer the requested boundary:

- **Data only:** prepare and validate the recipe, then hand outputs to the user.
- **Full prototype:** prepare or reuse data and iterate on local specs.
- **Spec only:** work from an existing recipe/output without changing scientific
  preparation unless the visualization exposes a real data-contract problem.
- **Publish:** assess and record rights, prepare or reuse accepted outputs,
  publish them, verify the hosted release, and update the requested consumers.

For a new recipe, clarify the biological question, audience, and visual
hypothesis; inspect relevant GenomeSpy documentation/examples; research source
identity, scale, assembly, coordinates, and redistribution evidence; and propose
the recipe ID, pinned input, outputs, validation, and local spec concept before
an ambiguous or expensive implementation.

Keep all data in ignored recipe directories. Use pinned inputs for accepted
runs, preserve scientific transformations in recipe scripts, keep
presentation-only logic in specs, and record compact provenance plus real source
and visualization rationale. Write original material and do not reproduce
third-party source text.

Validate the recipe and local spec at the requested scope. Hand off commands,
output contracts, validation evidence, uncertainties, and remaining promotion
work.

For publication work, apply `docs/rights-and-publication.md` and write the
decision in the recipe's `RIGHTS.md`. Clear authoritative open-data or
unrestricted-use evidence normally supports hosting; stop and ask only when the
evidence is genuinely ambiguous, contradictory, or restricted.

Infer external scope from the original request. A request to prepare or
prototype is local-only. A request to prepare and publish, or to publish an
existing recipe, includes the rights review, upload, hosted-release checks, and
requested consumer updates without a second approval step. Do not mutate S3,
GitHub, catalogs, or canonical GenomeSpy examples when those actions are outside
the requested scope.
