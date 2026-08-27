# Data rights and publication

Repository CC0 never licenses input or output data. Each recipe's `RIGHTS.md`
determines whether its outputs may be placed in GenomeSpy-managed storage.

## Evidence

Use an authoritative provider license, terms page, data-use policy,
public-domain statement, or written permission. Explicit unrestricted-use or a
standard open-data license is normally enough unless dataset-specific terms
conflict with it; provider email is not required merely because the policy uses
different wording.

Public access, an API, a paper citation, an existing mirror, or an old GenomeSpy
URL is not evidence by itself. Confirm that the terms cover the exact input and
the output being hosted: original bytes, a near-complete transformation, a
reduced extract, or synthetic data. For combined datasets, assess every
contributing source.

Preserve attribution, notices, citations, share-alike terms, and other
conditions. Controlled-access or personally identifying data is not suitable
for ordinary public S3 hosting. If evidence is genuinely ambiguous,
contradictory, or restrictive, keep the output local and ask the user.

## Recipe rights record

Every concrete recipe has a `RIGHTS.md` with:

1. the exact inputs and outputs covered;
2. authoritative evidence links;
3. a short interpretation;
4. required conditions; and
5. one decision: **eligible for GenomeSpy-managed hosting**, **use the
   authoritative upstream URL**, **local-only: prohibited**, or **local-only:
   unresolved**.

Include the review date. Keep the assessment concise and avoid copying policy
text. The recipe README links to it instead of restating it.

## Publication

If the user's request includes publication and the rights decision is clear,
the same workflow may upload and verify the files; no separate upload request
is needed. Otherwise preparation and prototyping remain local-only.

For a release:

- confirm the input identity, output fingerprints, rights record, and companion
  files;
- use the [canonical versioned object layout](storage-layout.md);
- provide compact provenance and required notices that link to the exact recipe
  commit;
- verify downloaded checksums and relevant HTTP behavior such as ranges, CORS,
  content type, and companion-file discovery;
- update requested public GenomeSpy specs only after the hosted files work.

Do not store deployment state in recipe records. The object store is the source
of truth. Future synchronization tooling can compare S3 objects with the paths
and checksums in `provenance.json` and its proposed `distribution.baseUrl`,
transfer missing or mismatched artifacts, and verify them.
