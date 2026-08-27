# Hosted data layout

Rights-cleared example data use this canonical CloudFront layout:

```text
https://data.genomespy.app/datasets/<recipe-id>/<release-id>/<artifact>
```

The corresponding S3 object key omits the host:

```text
datasets/<recipe-id>/<release-id>/<artifact>
```

`<recipe-id>` is the recipe directory name. `<release-id>` starts at `v1` and
changes when output bytes, scientific meaning, or the file contract changes.
Published releases are immutable; do not replace files in an existing release.

Artifact paths preserve their layout relative to the recipe's `output/`
directory. For example:

```text
output/samples/S96/segments.tsv.gz
→ https://data.genomespy.app/datasets/example-recipe/v1/samples/S96/segments.tsv.gz
```

## Recipe record

An eligible recipe records its proposed release root in `provenance.json`:

```json
{
  "distribution": {
    "baseUrl": "https://data.genomespy.app/datasets/example-recipe/v1/"
  }
}
```

This is a placement contract, not deployment state. The object store remains
the source of truth for what is present.

## Release sidecars

Each release root should contain:

- `README.md`, with the dataset description, required notices, authoritative
  source links, and a link to the exact GitHub recipe commit;
- `provenance.json`, with input identities, parameters, tool versions, and
  artifact fingerprints sufficient to verify the release.

The sidecar README must state that the recipe repository's CC0 dedication does
not license adjacent data. Add any license or notice file required by the
recipe's `RIGHTS.md`.

Canonical GenomeSpy specs should use the versioned URLs. Older unversioned or
`sample-data/` URLs may remain as compatibility aliases when rights permit, but
they are not the canonical location for new releases.
