# Data-rights review

## Scope

This review covers the six simulated hg19 ASCAT example inputs listed in
`provenance.json`, the generated `ASCAT_objects.Rdata` intermediate, and all TSV
outputs for S17, S36, S54, S64, S77, S84, S96, S97, and S100.

## Evidence and interpretation

The authoritative [ASCAT repository](https://github.com/VanLoo-lab/ascat)
distributes the exact example inputs at the pinned commit under GPL-3. This
supports redistributing the inputs and transformations under those terms. The
files are simulated tumor examples, not participant measurements. Van Loo et
al., [Allele-specific copy number analysis of tumors](https://doi.org/10.1073/pnas.1009843107),
is the scientific citation.

Running GPL software does not by itself make generated data copyrightable or
automatically GPL-covered. Preserving the upstream notice and source link is a
conservative condition because these outputs derive closely from example data
distributed in the GPL repository.

## Conditions

- Identify ASCAT, the pinned commit, and the Van Loo et al. citation.
- Include the upstream GPL-3 notice and source link.
- Describe the TSVs as GenomeSpy-produced transformations.
- Link to the exact recipe commit used to create them.
- Do not imply that repository CC0 covers data or intermediates.

## Decision

Eligible for GenomeSpy-managed hosting under the conditions above.

Reviewed: 2026-08-27
