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
| [`tcga-brca-gdc-pik3ca-mutations`](recipes/tcga-brca-gdc-pik3ca-mutations/) | Recurrent PIK3CA protein changes in breast cancer | GRCh38 input; protein coordinates | Lollipop and protein-domain tracks |
| [`tcga-ov-firehose-gistic2`](recipes/tcga-ov-firehose-gistic2/) | Recurrent ovarian-cancer copy-number changes | hg19 | GISTIC scores and lesion intervals |
| [`dynseq-spi1-bqtl`](recipes/dynseq-spi1-bqtl/) | Allele-specific SPI1 model importance scores | GRCh38 | Nucleotide-resolution BigWig comparison |
| [`encode-atac-grch38`](recipes/encode-atac-grch38/) | Multi-file ATAC signal integration fixture | GRCh38 | SampleView-driven BigWig tracks |
| [`encode-h3k27ac-chip-seq-grch38`](recipes/encode-h3k27ac-chip-seq-grch38/) | Multi-file H3K27ac ChIP-seq integration fixture | GRCh38 | SampleView-driven BigWig tracks |

## How recipes work

Each recipe keeps three durable records:

- `README.md`: purpose, rationale, commands, outputs, and limitations;
- `provenance.json`: release ID, exact inputs, and the last accepted run;
- `RIGHTS.md`: evidence and conditions for redistributing the data.

Scripts live under `scripts/`. Local GenomeSpy prototypes live under `specs/`
and load generated files with `../output/...` URLs. These ignored directories
make iteration ergonomic:

- `download/` — upstream inputs;
- `work/` — intermediate and temporary files;
- `output/` — final artifacts used by local specs.

Start with [the recipe guide](docs/recipe-guide.md). Data intended for public
hosting must also pass [the rights protocol](docs/rights-and-publication.md)
and follow the [hosted data layout](docs/storage-layout.md). Rights-cleared
outputs can be uploaded manually with the explicit, manifest-driven
[publishing tool](docs/publishing.md).

## AWS publishing quick start

Use a named, non-root AWS profile with temporary credentials and permissions
limited to listing the target bucket and reading and writing `datasets/*`.
Credentials and profile configuration belong under `~/.aws/`, never in this
repository. Authenticate using the configured IAM Identity Center profile:

```bash
aws sso login --profile genomespy-publisher
aws sts get-caller-identity --profile genomespy-publisher
```

Do not publish if the reported ARN ends in `:root`; see the
[AWS root-user best practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/root-user-best-practices.html).
The publishing identity does not need `s3:DeleteObject`.

The managed dataset bucket is `genome-spy` in `eu-north-1`.

Copy the target template to the ignored local configuration file:

```bash
cp .genomespy-publish.example.toml .genomespy-publish.toml
```

The template records the production bucket, region, AWS profile, and expected
owner. It contains no credentials. Explicit command-line options still
override the selected target.

The smallest hosting-eligible release is
`tcga-brca-gdc-pik3ca-mutations`: two data artifacts totaling 1,260 bytes.
First verify its ignored local outputs and inspect the hosted state:

```bash
uv run --script \
  recipes/tcga-brca-gdc-pik3ca-mutations/scripts/prepare.py --verify-only

./tools/publish_dataset.py status tcga-brca-gdc-pik3ca-mutations
```

`status` is read-only and works without committed recipe changes. Before
`plan`, `publish`, or `verify`, commit the complete intended recipe change
yourself; the tool never creates commits. Preview the exact operation without
writing, then upload and verify:

```bash
./tools/publish_dataset.py plan tcga-brca-gdc-pik3ca-mutations
./tools/publish_dataset.py publish tcga-brca-gdc-pik3ca-mutations
./tools/publish_dataset.py verify tcga-brca-gdc-pik3ca-mutations
```

See the [full publishing guide](docs/publishing.md) for target configuration,
manifest, immutability, symlink, and public-verification details.

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

All original repository-authored material—including wrangling scripts,
publishing tools, tests, documentation, and specs—is dedicated under
[CC0 1.0 Universal](LICENSES/CC0-1.0.txt). This dedication never licenses
datasets or third-party material. See [LICENSE-SCOPE.md](LICENSE-SCOPE.md).
