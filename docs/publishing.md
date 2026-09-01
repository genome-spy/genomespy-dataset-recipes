# Publishing recipe outputs

The repository includes a manifest-driven S3 publisher. Its publication
operations only process recipe IDs named on the command line. A
`distribution.baseUrl` records hosting eligibility and placement; it never
causes a recipe to be published implicitly.

## Credentials and destination

The publisher invokes AWS CLI v2 and uses its normal credential chain. Keep
credentials outside this repository. A named IAM Identity Center profile is the
preferred interactive setup:

```bash
aws configure sso --profile genomespy-publisher
aws sso login --profile genomespy-publisher
aws sts get-caller-identity --profile genomespy-publisher
```

The profile configuration and temporary SSO tokens live under `~/.aws/`, not in
recipe metadata or the repository configuration. The publishing role should
have only the S3 list, read, and write permissions needed under `datasets/`; it
does not need `s3:DeleteObject`. Supplying the bucket owner account ID protects
against accidentally targeting a same-named bucket owned by another account.

## Local targets

Copy the tracked example to the ignored local dotfile:

```bash
cp .genomespy-publish.example.toml .genomespy-publish.toml
```

The file defines named destinations:

```toml
default_target = "production"

[targets.production]
bucket = "genome-spy"
profile = "genomespy-publisher"
region = "eu-north-1"
expected_bucket_owner = "123456789012" # Replace with the bucket owner's account ID.
```

These values identify infrastructure, not credentials. The repository ignores
`.genomespy-publish.toml`; never add access keys or SSO tokens to it. A target
may also contain `skip_public_verification`, `cors_origin`, or an
`allow_source_roots` array. Select another configured target with `--target`;
`GENOMESPY_PUBLISH_TARGET` can supply the selection for a shell session.
Precedence is explicit command-line option, selected target, then an applicable
environment fallback. Use `--config PATH` for a different configuration file.
The tool prints the resolved S3 destination and AWS principal before processing
a release.

## Commands

Check which declared recipe artifacts are absent from S3:

```bash
./tools/publish_dataset.py status
```

With no recipe IDs, `status` checks every recipe that declares a managed-hosting
artifact inventory. Give one or more IDs after `status` to limit the report.
This action is read-only, does not imply that every listed recipe should be
uploaded, and works even when the ignored local `output/` files are absent. It
uses paginated S3 listings to compare object presence and size with
`distribution.artifacts`. Use `verify` when full object metadata, checksums,
and public CloudFront behavior must also be checked. Missing artifacts are
reported as information rather than treated as a failed command, since a
publishable recipe need not actually be published.

Preview an explicitly selected release without writing:

```bash
./tools/publish_dataset.py plan encode-k562-re2g
```

Publish exactly the selected recipe or recipes:

```bash
./tools/publish_dataset.py publish \
  encode-k562-re2g nist-hg002-grch38-bam-slice
```

Verify an existing release without uploading:

```bash
./tools/publish_dataset.py verify encode-k562-re2g
```

`publish` and `verify` check the public CloudFront URLs, byte ranges, content
types, and CORS by default. Add `--deep` to download every selected data object
and verify its public SHA-256 checksum. Use `--skip-public-verification` only
when the CloudFront endpoint is intentionally not ready yet.

## Safety and release behavior

Before a publication action contacts S3, the tool requires:

- an eligible decision in `RIGHTS.md`;
- a canonical versioned `distribution.baseUrl`;
- an explicit `distribution.artifacts` inventory;
- local sizes and SHA-256 fingerprints that match the inventory; and
- a completely committed recipe source tree, so the generated release README
  can link to the latest commit that changed that recipe. Unrelated later
  repository commits do not change the generated sidecar.

These local-artifact and committed-source requirements apply to `plan`,
`publish`, and `verify`. Use `status` for a remote inventory from a clean clone
that does not have ignored output files.

The publication actions compare each expected key using `HeadObject`. Missing
keys are created with SHA-256 validation and `If-None-Match: *`. Matching keys
are left alone. A conflicting key stops the release and is never overwritten.
The tool does not delete objects, implicitly publish recipes found by `status`,
or upload unlisted files from an ignored `output/` directory.

Data objects are uploaded before `README.md` and `provenance.json` sidecars.
The generated README includes the rights record and the exact recipe commit.
The current implementation uses conditional single-request uploads and rejects
an individual artifact larger than 5 GB rather than falling back to an unsafe
overwrite-capable transfer.

Artifact symlinks are resolved and checked against the manifest before upload.
The sibling `example-dataset-wrangling` workspace is trusted automatically for
the existing migrated recipes. For another local source workspace, add
`--allow-source-root PATH`; this scopes the exception to that directory rather
than allowing arbitrary symlink targets. Publication prints a compact summary
when selected artifacts resolve outside their recipe directory.
