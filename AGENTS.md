# GenomeSpy dataset recipe instructions

This repository contains reproducible workflows for GenomeSpy example data. It
must not contain dataset artifacts.

## Work on a recipe

- Read `docs/recipe-guide.md`, `docs/rights-and-publication.md`, and the target
  recipe's `README.md`, `provenance.json`, and `RIGHTS.md`.
- Use a stable lowercase kebab-case recipe ID. Start from `recipes/_template/`.
- Keep inputs, intermediates, and outputs only in ignored `download/`, `work/`,
  and `output/` directories. Never force-add them.
- Put prototype specs under `specs/` and use `../output/...` data URLs.
- Record the real source-selection rationale and, when it exists, why the data
  make a useful GenomeSpy example.
- Keep accepted inputs pinned. Record exact source identity, checksums,
  parameters, meaningful tool versions, output fingerprints, validation, and
  limitations in `provenance.json`.
- Every `provenance.json` has a `releaseId` such as `v1`. Increment it when
  accepted output bytes, scientific meaning, included samples or fields, or
  the output file contract changes. Do not increment it for documentation,
  rights evidence, or refactors that reproduce the accepted outputs exactly.
- Prefer one obvious preparation entrypoint and readable recipe-local code.
  Add shared abstractions only after repeated need.
- Python entrypoints use PEP 723 metadata and uv script locks when they have
  third-party dependencies. Use type annotations, `pathlib.Path`, deterministic
  output, and fail-fast validation. R and shell are fine when clearer.

## Rights and authorship

- A public URL does not establish permission to mirror data. Record
  authoritative evidence, interpretation, conditions, and the decision in
  `RIGHTS.md`. Unresolved or prohibited outputs stay local.
- Only data that the rights record permits may be placed in GenomeSpy-managed
  storage. Eligible recipes record a proposed `distribution.baseUrl` using
  `docs/storage-layout.md`; its version must match `releaseId`. Deployment
  state is not repository metadata.
- Write original scripts, prose, and specs. Do not copy, closely adapt,
  translate, or vendor copyrighted source code into CC0-covered paths. Treat
  LLM output as provenance-uncertain and inspect it for copied material.
- CC0 covers all original repository-authored material, including wrangling
  scripts, tooling, tests, documentation, specs, and authored metadata. It
  never covers datasets or third-party material.

## Scope and handoff

- Preparing or prototyping is local-only. Publishing includes the rights check,
  upload, verification, and requested consumer changes when the user put those
  actions in scope; do not ask for a separate upload approval.
- Do not mutate S3, GitHub, or the canonical GenomeSpy repository unless the
  request includes that external change.
- Run the recipe's documented validation and `uv run python tools/check_repo.py`
  before handoff. Use the full checks listed in the root README for repository
  changes.
