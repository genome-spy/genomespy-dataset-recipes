# GenomeSpy dataset recipe instructions

This repository contains reproducible preparation workflows and compact
metadata for GenomeSpy example datasets. It contains no dataset artifacts.

## Before editing

- Read `docs/recipe-guide.md`, `docs/rights-and-publication.md`, and the target
  recipe's `README.md` and `RIGHTS.md`.
- Treat downloaded, intermediate, processed, mirrored, and hosted files as data,
  even when they are small or publicly accessible.
- Keep data only under the recipe's ignored `download/`, `work/`, `output/`, or
  `publish/` directory. Never force-add a file from those directories.

## Recipe work

- Use a stable lowercase kebab-case recipe ID and copy `recipes/_template/`.
- Record exact source identity, checksums when available, assembly or coordinate
  system, transformations, meaningful tool versions, validation, and known
  limitations.
- Keep ordinary runs pinned. Make source discovery or refresh an explicit,
  documented action.
- Put local GenomeSpy specs under `specs/` and load generated files through
  `../output/...` URLs. Do not embed dataset tables in a spec.
- Record why the source was selected and, when there is a genuine reason, why it
  is useful for a GenomeSpy visualization. Do not invent a rationale.
- Prefer readable recipe-local logic over shared abstractions. Add shared
  tooling only after repeated recipes demonstrate the same nontrivial need.
- Run `uv run python tools/check_repo.py` before handoff, plus the recipe's own
  preparation, validation, and preview checks.

## Python, R, and external tools

- Python entrypoints use PEP 723 metadata and isolated uv script environments.
  Commit the adjacent script lock when third-party Python dependencies exist.
- Use type annotations, `pathlib.Path`, explicit encodings, deterministic order,
  atomic writes, and fail-fast validation.
- R and shell are allowed when they express the workflow clearly. Do not add a
  Python adapter for appearance alone. Record meaningful runtime, package, and
  external-tool versions.

## Authorship and third-party material

- Write original scripts, prose, and specs. Do not copy, closely adapt,
  translate, or vendor third-party source text into CC0-covered paths.
- Use dependencies through their documented public APIs. A dependency's license
  does not authorize presenting copied implementation text as CC0.
- Treat LLM output as provenance-uncertain. Do not ask a model to reproduce an
  external implementation, and inspect generated material for source-specific
  comments, identifiers, structure, or license notices.
- Include source text only when it is demonstrably CC0/public-domain or explicit
  permission authorizes CC0 redistribution. Record durable evidence first. If
  provenance is uncertain, implement independently or stop for review.

## Rights and external changes

- Public access, downloadability, a paper citation, or existing GenomeSpy
  hosting does not establish permission to mirror original or derived data.
- Record the exact evidence, interpretation, conditions, decision, and review
  date in the recipe's `RIGHTS.md`. A standard open-data license or an
  authoritative unrestricted-use statement normally supports hosting unless
  dataset-specific terms conflict with it.
- Keep unresolved or prohibited outputs local-only. Ask the user only when the
  evidence is genuinely ambiguous, contradictory, or restricted.
- Infer publication scope from the request. “Prepare” or “prototype” is local
  only; “prepare and publish” or “publish” includes the documented rights
  review, S3/CloudFront release, verification, and requested consumer updates.
  Do not request a separate upload approval when publication was already in
  scope and the evidence satisfies the protocol.
- Do not upload data, mutate S3/CloudFront, create releases, edit the canonical
  GenomeSpy repository, or push GitHub changes when those actions are outside
  the user's requested scope.
- CC0 applies only to repository-authored wrangling scripts, files named
  `README.md`, and recipe GenomeSpy specs. It never applies to data.
