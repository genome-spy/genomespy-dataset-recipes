# Data rights and publication

This repository can document and transform a dataset without having permission
to host it. Each concrete recipe records its hosting decision in `RIGHTS.md`.
That record, rather than repository CC0, determines whether recipe outputs may
be published through GenomeSpy-managed storage.

## What counts as sufficient evidence

Use an authoritative source such as the data provider's license, terms,
data-use policy, public-domain declaration, or written permission. A standard
open-data license or an explicit statement allowing unrestricted use is
normally sufficient unless dataset-specific terms conflict with it. Do not
require a provider email merely because the policy does not use the word
“redistribution.”

Public accessibility alone is not evidence. Neither is an API, a paper
citation, an existing third-party mirror, or an older GenomeSpy URL. Check that
the evidence applies to the exact released source and to the kind of output
being hosted: original bytes, a near-complete transformation, a reduced extract,
or a synthetic result.

When a recipe combines sources, assess every output against all contributing
sources. Preserve any attribution, notice, share-alike, naming, or citation
conditions. Controlled-access or personally identifying data requires an
appropriate sharing mechanism and is not eligible for ordinary public S3
hosting.

If authoritative evidence is genuinely ambiguous, contradictory, or
dataset-specific, leave the output local-only and ask the user. Do not escalate
clear unrestricted-use language into a legal or provider review by default.

## Recipe decision record

Every concrete recipe has a `RIGHTS.md` containing:

1. the exact source and outputs covered;
2. authoritative evidence links;
3. a short interpretation of how the evidence applies;
4. attribution or notice conditions;
5. one of these decisions:
   - **eligible for GenomeSpy-managed hosting**;
   - **use the authoritative upstream URL**;
   - **local-only: prohibited**;
   - **local-only: unresolved**;
6. the review date.

Keep the corresponding machine-readable summary in `recipe.yaml`:

- source `redistribution: allowed`, `prohibited`, or `unresolved`;
- output `publication: hosted`, `upstream`, or `local-only`.

`hosted` means the evidence supports a GenomeSpy-managed release. It does not
claim that the file has already been uploaded. The recipe README summarizes the
decision and links to `RIGHTS.md`; it does not duplicate the full assessment.

## Scope of the user's request

Do not create an extra approval ceremony. Interpret the original request:

- **Prepare or prototype** means local recipe work only.
- **Prepare and publish** includes rights assessment, S3/CloudFront publication,
  and requested consumer updates.
- **Publish an existing recipe** uses its current outputs and accepted rights
  record.

When publication is already in scope and the evidence clearly satisfies this
protocol, proceed without requesting a second upload authorization. Stop and ask
only if rights remain unresolved, credentials or target details are missing, or
the requested external change materially exceeds the original scope.

## Release checklist

For an eligible output within a publication request:

1. Reconfirm the source identity, accepted `RIGHTS.md`, output checksums, and all
   companion files.
2. Use an immutable key such as
   `datasets/<recipe-id>/<release-id>/...` or
   `reference/<recipe-id>/<release-id>/...`.
3. Add compact README/provenance sidecars with required notices and a link to
   the exact GitHub recipe commit.
4. State explicitly that repository CC0 does not license adjacent data.
5. Upload the files and verify CloudFront checksums, byte ranges, CORS, content
   type, content encoding, and companion discovery as applicable.
6. Update requested canonical GenomeSpy specs only after the release works.
7. Decide whether each legacy URL remains as a rights-cleared compatibility
   object or requires an explicitly authorized removal.

Where hosting is prohibited or unresolved, use an immutable authoritative URL
when practical. Otherwise keep the example local, redesign it, or retire it
rather than embedding the same records in a CC0-covered specification.
