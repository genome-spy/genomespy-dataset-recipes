# GenomeSpy dataset recipes

Reproducible preparation scripts and provenance for datasets used in
[GenomeSpy](https://genomespy.app/) examples and visualization prototypes.

> [!IMPORTANT]
> This repository contains recipes and compact metadata, **not datasets**.
> Downloaded, intermediate, processed, mirrored, and hosted data are outside the
> repository and keep their own upstream legal status. The repository's CC0
> dedication does not license any data.

## Recipes

| Recipe | Purpose | Coordinates | Status | Consumer |
| --- | --- | --- | --- | --- |
| [`encode-k562-re2g`](recipes/encode-k562-re2g/) | ENCODE-rE2G regulatory element–gene links for K562 | GRCh38 | Ready; hosting eligible | Local GenomeSpy prototype |

`Draft` recipes are usable for local exploration. Their source identity,
validation, publication rights, or public consumer may still need review.
`Hosting eligible` means an accepted recipe-level rights record supports a
GenomeSpy-managed release; it does not mean the files are already deployed.

## Quick start

Install [uv](https://docs.astral.sh/uv/), clone the repository, and set up the
small development environment:

```bash
uv sync --locked
uv run python tools/check_repo.py
```

Each Python recipe has its own PEP 723 environment. The K562 recipe uses only
the Python standard library, downloads about 3.6 MB when its pinned source is
not cached, and writes ignored outputs beside the recipe:

```bash
uv run --locked --script recipes/encode-k562-re2g/scripts/prepare.py
```

To view its local spec, start the GenomeSpy development server from a sibling
GenomeSpy checkout with `npm start`, then open:

```text
http://localhost:8080/?spec=private/genomespy-dataset-recipes/recipes/encode-k562-re2g/specs/overview.json
```

Recipe-specific downloads, system tools, runtimes, and validation commands are
documented in each recipe README.

## Workflow

1. Start from a data or visualization idea.
2. Research the authoritative source, assembly, coordinate conventions, scale,
   and redistribution terms.
3. Prepare data in the recipe's ignored `download/`, `work/`, and `output/`
   directories.
4. Prototype specs under `specs/` using `../output/...` URLs.
5. Keep scientific shaping in the recipe and presentation logic in the spec.
6. Validate the result and record compact provenance.
7. If publication was requested and the recipe's rights record is eligible,
   publish and verify the release without requiring a second approval. Otherwise
   stop at the validated local prototype.

See the [recipe guide](docs/recipe-guide.md) for naming, Python/uv conventions,
metadata, validation, and handoff expectations. See
[rights and publication](docs/rights-and-publication.md) before proposing any
hosted release.

## Ask an agent

The repository includes [agent instructions](AGENTS.md) and a
[GenomeSpy example-development skill](.agents/skills/develop-genomespy-example/SKILL.md).
A typical request is:

> Add dataset xyz for a GenomeSpy example. Follow this repository's recipe,
> naming, provenance, and rights guidelines. Keep all data out of Git, prepare a
> local spec using relative output URLs, and do not publish anything.

For a narrower task, say “prepare the data only” or “work only on specs for the
existing recipe.”

For the complete workflow, say:

> Prepare and publish dataset xyz for a GenomeSpy example. Follow the repository
> rights protocol, publish only if the evidence qualifies, and update the
> requested GenomeSpy consumer after verifying the hosted release.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Keep contributions recipe-sized and do
not add source or generated data, vendored code, credentials, signed URLs, or
bulk API responses.

## Licensing

To the extent any rights exist, repository-authored wrangling scripts, files
named `README.md`, and GenomeSpy specs under recipe `specs/` directories are
dedicated to the public domain under
[CC0 1.0 Universal](LICENSES/CC0-1.0.txt).

No data, source lock, provenance record, policy document, lockfile, or other
unlisted file is covered. See [LICENSE-SCOPE.md](LICENSE-SCOPE.md) for the exact
boundary.
