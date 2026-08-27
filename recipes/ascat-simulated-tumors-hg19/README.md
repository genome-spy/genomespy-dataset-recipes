# ASCAT simulated tumors on hg19

This recipe prepares nine representative simulated tumor profiles from ASCAT's
official hg19 example data. One GenomeSpy spec shows allele-specific copy
number, LogR, and B-allele frequency for sample S96. A second spec prototypes an
interactive purity/ploidy fitting surface across all nine selected samples.

The recipe is `ready`. The outputs and both local specs have been validated.
The outputs are eligible for GenomeSpy-managed hosting under the GPL-3 terms
recorded in `RIGHTS.md`, but this recipe has not uploaded them.

## Why this source

The official ASCAT repository includes simulated tumor and matched-germline
LogR/BAF tables plus hg19 GC and replication-timing tracks. Simulated profiles
avoid redistributing patient measurements while preserving realistic ASCAT
segmentation and purity/ploidy behavior.

The selected samples are S17, S36, S54, S64, S77, S84, S96, S97, and S100.
Together they span accepted tumor purities from 0.24 to 1.0 and ploidies from
1.7 to 3.4. S96 was retained for the overview because its 84 final segments
give a varied whole-genome copy-number profile.

Source: [VanLoo-lab/ascat](https://github.com/VanLoo-lab/ascat) at commit
`61ddf3b24453eea91134798cc41d4e828a82fa90` (ASCAT R 3.2.0).

Citation: Van Loo et al., [Allele-specific copy number analysis of
tumors](https://doi.org/10.1073/pnas.1009843107).

## Why it works as a GenomeSpy example

The overview combines genome-wide intervals with dense probe-level points and
coordinated allele-specific copy-number, LogR, and BAF tracks. The fitting spec
adds linked parameters, calculated copy numbers, a purity/ploidy objective
surface, and dynamic sample switching. The data are small enough for eager TSV
loading but rich enough to demonstrate coordinated genomic analytical views.

## Preparation

Requirements are R 4.5.2, ASCAT R 3.2.0, and `gzip`. Put the six files pinned in
`sources.lock.json` under ignored `download/`. Generate the ASCAT intermediate:

```bash
ASCAT_INPUT_DIR=recipes/ascat-simulated-tumors-hg19/download \
ASCAT_WORK_DIR=recipes/ascat-simulated-tumors-hg19/work \
Rscript recipes/ascat-simulated-tumors-hg19/scripts/prepare-objects.R
```

Then wrangle and validate the visualization artifacts:

```bash
ASCAT_DATA_DIR=recipes/ascat-simulated-tumors-hg19/work \
Rscript recipes/ascat-simulated-tumors-hg19/scripts/wrangle.R

ASCAT_DATA_DIR=recipes/ascat-simulated-tumors-hg19/work \
Rscript recipes/ascat-simulated-tumors-hg19/scripts/validate.R
```

For the independent fitting-distance comparison, check out the pinned ASCAT
commit outside this repository and run:

```bash
ASCAT_DATA_DIR=recipes/ascat-simulated-tumors-hg19/work \
ASCAT_SOURCE_DIR=/path/to/pinned/ascat \
Rscript recipes/ascat-simulated-tumors-hg19/scripts/compare-distances.R
```

The `ASCAT_SOURCE_DIR` checkout is used as a dependency; none of its GPL source
code is copied into this CC0-covered recipe. A clean run from the six pinned
tables reproduced the accepted `ASCAT_objects.Rdata` checksum exactly.

## Outputs and coordinates

The recipe writes deterministic gzip files:

- `output/fits.tsv.gz`, with one accepted solution per selected sample;
- `output/samples/<sample>/segments.tsv.gz`, final allele-specific calls;
- `output/samples/<sample>/fit-segments.tsv.gz`, joint segmented LogR/BAF runs;
- `output/samples/<sample>/raw.tsv.gz`, 10,000 probe-level values.

Chromosomes use hg19 names without a `chr` prefix. Positions are one-based probe
coordinates as supplied by ASCAT. Segment starts and ends are inclusive probe
positions. The wrangler preserves upstream column names because both specs and
ASCAT terminology already rely on them.

The previous GenomeSpy overview used old hg18 files from an older ASCAT package.
This recipe intentionally migrates that visualization to the maintained hg19
example. It does not preserve the hg18 artifacts as recipe outputs.

## Validation

All nine samples validate against the saved ASCAT objects. Every raw table has
10,000 probes; final segment counts range from 23 to 88. S96 has 84 final and 84
fit segments, with 5,927 retained heterozygous BAF values.

The complete source-to-intermediate pipeline reproduces the accepted R object
byte for byte. The GenomeSpy fitting objective was compared against ASCAT R 3.2.0's distance
matrix for every selected sample. Log-distance correlations are 1.0 and the
largest absolute numerical difference is `8.74e-11`. Two consecutive wrangling
runs produced identical gzip checksums.

## Local visualizations

Start the GenomeSpy development server and open either spec:

```text
http://localhost:8080/?spec=private/genomespy-dataset-recipes/recipes/ascat-simulated-tumors-hg19/specs/copy-number-overview.json
http://localhost:8080/?spec=private/genomespy-dataset-recipes/recipes/ascat-simulated-tumors-hg19/specs/purity-ploidy-fitting.json
```

## Data rights

The accepted [data-rights review](RIGHTS.md) concludes that the official
GPL-3-licensed ASCAT example files and these derived tables may be hosted if the
GPL notice, source link, attribution, and citation accompany the release.

Repository CC0 covers this README, the authored preparation and validation
scripts, and the local GenomeSpy specs. It does not cover the ASCAT inputs,
intermediate R data, or generated TSV files.
