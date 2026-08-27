# Data-rights review

## Scope

This review covers the six simulated hg19 `ExampleData` inputs identified in
`sources.lock.json`, the generated `ASCAT_objects.Rdata` intermediate, and all
TSV outputs produced by this recipe for S17, S36, S54, S64, S77, S84, S96,
S97, and S100.

## Evidence

- The authoritative [ASCAT GitHub repository](https://github.com/VanLoo-lab/ascat)
  declares GPL-3 and includes the exact example input files at the pinned
  commit.
- The local source files used for the accepted run are byte-identical to those
  six files at commit `61ddf3b24453eea91134798cc41d4e828a82fa90`.
- Van Loo et al., [Allele-specific copy number analysis of
  tumors](https://doi.org/10.1073/pnas.1009843107), is the requested scientific
  citation for ASCAT.

## Interpretation

The official repository distributes these simulated example files under
GPL-3. Public hosting of the files transformed by this recipe is permitted when
the GPL-3 conditions are preserved. The inputs are simulated tumor examples,
not measurements from human research participants.

## Conditions

- Identify ASCAT, the pinned upstream commit, and the Van Loo et al. citation.
- Include a GPL-3 notice and a link to the corresponding upstream source.
- Mark the hosted TSVs as GenomeSpy-produced transformations of ASCAT example
  data; do not present them as original ASCAT release files.
- Make the recipe source used to produce the hosted form available through its
  exact GitHub commit.
- Do not apply or imply the recipe repository's CC0 dedication to any data or
  intermediate file.

## Decision

Eligible for GenomeSpy-managed hosting subject to the conditions above. This
decision records eligibility; it does not claim that the files have already
been uploaded.

Reviewed: 2026-08-27
