# GenomeSpy dataset recipes

Reproducible wrangling scripts and provenance for datasets used in
[GenomeSpy](https://genomespy.app/) examples.

> [!IMPORTANT]
> This repository contains recipes, not data. Inputs, intermediate files, and
> outputs stay in ignored directories and retain their upstream legal status.
> The repository's CC0 dedication never applies to data.

## Recipes

| Recipe | Use | Assembly | Specs |
| --- | --- | --- | --- |
| [`encode-k562-re2g`](recipes/encode-k562-re2g/) | Regulatory element–gene links | GRCh38 | Link and endpoint tracks |
| [`nist-hg002-grch38-bam-slice`](recipes/nist-hg002-grch38-bam-slice/) | Indexed read-alignment slice | GRCh38 | BAM pileup |
| [`ascat-simulated-tumors-hg19`](recipes/ascat-simulated-tumors-hg19/) | Simulated allele-specific copy number | hg19 | Copy-number and purity/ploidy views |
| [`hcc1954-castle-severus-wakhan`](recipes/hcc1954-castle-severus-wakhan/) | Matched structural variants and copy number | GRCh38 | SV links and copy-number segments |

## How recipes work

Each recipe keeps three durable records:

- `README.md`: purpose, rationale, commands, outputs, and limitations;
- `provenance.json`: exact inputs and the last accepted run;
- `RIGHTS.md`: evidence and conditions for redistributing the data.

Scripts live under `scripts/`. Local GenomeSpy prototypes live under `specs/`
and load generated files with `../output/...` URLs. These ignored directories
make iteration ergonomic:

- `download/` — upstream inputs;
- `work/` — intermediate and temporary files;
- `output/` — final artifacts used by local specs.

Start with [the recipe guide](docs/recipe-guide.md). Data intended for public
hosting must also pass [the rights protocol](docs/rights-and-publication.md)
and follow the [hosted data layout](docs/storage-layout.md).

## Repository checks

Install [uv](https://docs.astral.sh/uv/) and run:

```bash
uv sync --locked
uv run python tools/check_repo.py
uv run ruff check .
uv run ruff format --check .
uv run python tools/typecheck.py
uv run pytest
```

Python recipe entrypoints use PEP 723 metadata and run independently with
`uv run --script <path>`. Recipes with third-party dependencies also commit a
script lock and use `--locked`.

## Asking an agent

A useful request is:

> Add dataset xyz for a GenomeSpy example. Follow this repository's guidance,
> keep all data out of Git, record enough provenance to reproduce the accepted
> outputs, assess redistribution rights, and prototype specs with relative
> output URLs. Do not publish or change another repository unless requested.

The repository includes [agent instructions](AGENTS.md) and a focused
[example-development skill](.agents/skills/develop-genomespy-example/SKILL.md).

## License

Repository-authored wrangling scripts, files named `README.md`, and recipe specs
are dedicated under [CC0 1.0 Universal](LICENSES/CC0-1.0.txt). Data and other
files are not. See [LICENSE-SCOPE.md](LICENSE-SCOPE.md).
