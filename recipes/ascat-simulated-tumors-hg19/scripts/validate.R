#!/usr/bin/env Rscript
# SPDX-License-Identifier: CC0-1.0

# Validate wrangled GenomeSpy TSVs against the saved ASCAT objects.

expected_segment_columns <- c(
    "sample",
    "chr",
    "startpos",
    "endpos",
    "nMajor",
    "nMinor",
    "logRMean",
    "bafMean",
    "nProbes"
)
expected_raw_columns <- c("SNP", "chr", "pos", "logR", "baf")
expected_fit_segment_columns <- c(
    "sample",
    "chr",
    "startpos",
    "endpos",
    "logRMean",
    "bafMean",
    "nProbes"
)

get_script_path <- function() {
    file_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
    if (length(file_arg) != 1) {
        stop("Run this script using Rscript.", call. = FALSE)
    }

    normalizePath(sub("^--file=", "", file_arg), mustWork = TRUE)
}

read_tsv <- function(path) {
    read.delim(
        path,
        header = TRUE,
        sep = "\t",
        quote = "",
        na.strings = "",
        check.names = FALSE,
        stringsAsFactors = FALSE
    )
}

assert <- function(condition, message) {
    if (!isTRUE(condition)) {
        stop(message, call. = FALSE)
    }
}

equal_values <- function(actual, expected) {
    isTRUE(all.equal(actual, expected, check.attributes = FALSE))
}

make_expected_fit_segments <- function(ascat_bc, sample, sample_index) {
    segmented_baf <- ascat_bc$Tumor_BAF_segmented[[sample_index]][, 1]
    snp_names <- rownames(ascat_bc$Tumor_BAF_segmented[[sample_index]])
    positions <- ascat_bc$SNPpos[snp_names, , drop = FALSE]
    segmented_logr <- as.numeric(
        ascat_bc$Tumor_LogR_segmented[snp_names, sample_index]
    )
    chromosomes <- as.character(positions$chrs)
    probe_positions <- as.integer(positions$pos)
    segmented_baf <- as.numeric(segmented_baf)

    run_start <- c(
        TRUE,
        chromosomes[-1] != chromosomes[-length(chromosomes)] |
            segmented_logr[-1] != segmented_logr[-length(segmented_logr)] |
            segmented_baf[-1] != segmented_baf[-length(segmented_baf)]
    )
    run_id <- cumsum(run_start)
    indices <- split(seq_along(run_id), run_id)

    do.call(
        rbind,
        lapply(
            indices,
            function(index) {
                data.frame(
                    sample = sample,
                    chr = chromosomes[index[1]],
                    startpos = probe_positions[index[1]],
                    endpos = probe_positions[index[length(index)]],
                    logRMean = segmented_logr[index[1]],
                    bafMean = segmented_baf[index[1]],
                    nProbes = length(index),
                    stringsAsFactors = FALSE
                )
            }
        )
    )
}

script_path <- get_script_path()
recipe_dir <- dirname(dirname(script_path))
data_dir <- Sys.getenv("ASCAT_DATA_DIR", file.path(recipe_dir, "download"))
output_dir <- Sys.getenv("ASCAT_OUTPUT_DIR", file.path(recipe_dir, "output"))

objects <- new.env(parent = baseenv())
load(file.path(data_dir, "ASCAT_objects.Rdata"), envir = objects)

fits <- read_tsv(file.path(output_dir, "fits.tsv"))
assert(
    identical(
        names(fits),
        c("sample", "rho", "psi", "ploidy", "goodnessOfFit")
    ),
    "fits.tsv has unexpected columns."
)

for (sample in fits$sample) {
    segment_path <- file.path(
        output_dir, "samples", sample, "segments.tsv"
    )
    raw_path <- file.path(output_dir, "samples", sample, "raw.tsv")
    fit_segment_path <- file.path(
        output_dir, "samples", sample, "fit-segments.tsv"
    )

    segments <- read_tsv(segment_path)
    raw <- read_tsv(raw_path)
    fit_segments <- read_tsv(fit_segment_path)
    source_segments <- objects$ascat.output$segments[
        objects$ascat.output$segments$sample == sample,
        c("sample", "chr", "startpos", "endpos", "nMajor", "nMinor")
    ]
    sample_index <- match(sample, objects$ascat.bc$samples)
    heterozygous_count <- nrow(
        objects$ascat.bc$Tumor_BAF_segmented[[sample_index]]
    )
    expected_fit_segments <- make_expected_fit_segments(
        objects$ascat.bc,
        sample,
        sample_index
    )

    assert(
        identical(names(segments), expected_segment_columns),
        paste(sample, "segment TSV has unexpected columns.")
    )
    assert(
        identical(names(raw), expected_raw_columns),
        paste(sample, "raw TSV has unexpected columns.")
    )
    assert(
        identical(names(fit_segments), expected_fit_segment_columns),
        paste(sample, "fit-segment TSV has unexpected columns.")
    )
    assert(
        nrow(segments) == nrow(source_segments),
        paste(sample, "segment count differs from ASCAT output.")
    )
    assert(
        nrow(raw) == nrow(objects$ascat.bc$SNPpos),
        paste(sample, "raw probe count differs from ASCAT input.")
    )
    assert(
        identical(as.character(segments$sample), source_segments$sample),
        paste(sample, "has incorrect sample identifiers.")
    )
    assert(
        identical(as.character(segments$chr), as.character(source_segments$chr)) &&
            equal_values(segments$startpos, source_segments$startpos) &&
            equal_values(segments$endpos, source_segments$endpos) &&
            equal_values(segments$nMajor, source_segments$nMajor) &&
            equal_values(segments$nMinor, source_segments$nMinor),
        paste(sample, "segment coordinates or copy-number calls changed.")
    )
    assert(
        identical(raw$SNP, rownames(objects$ascat.bc$SNPpos)) &&
            identical(as.character(raw$chr), objects$ascat.bc$SNPpos$chrs) &&
            identical(raw$pos, objects$ascat.bc$SNPpos$pos),
        paste(sample, "raw SNP coordinates or ordering changed.")
    )
    assert(
        sum(!is.na(raw$baf)) == heterozygous_count,
        paste(sample, "does not have the expected heterozygous BAF count.")
    )
    assert(
        equal_values(raw$logR, signif(raw$logR, digits = 3)) &&
            equal_values(raw$baf, signif(raw$baf, digits = 3)),
        paste(sample, "raw values are not rounded to three significant digits.")
    )
    assert(
        all(is.finite(segments$logRMean)) &&
            all(is.finite(segments$bafMean)) &&
            all(segments$bafMean >= 0 & segments$bafMean <= 1),
        paste(sample, "has invalid segment means.")
    )
    assert(
        sum(segments$nProbes) == nrow(raw),
        paste(sample, "segment probe counts do not cover the raw data.")
    )
    assert(
        nrow(fit_segments) == nrow(expected_fit_segments) &&
            identical(
                as.character(fit_segments$sample),
                expected_fit_segments$sample
            ) &&
            identical(
                as.character(fit_segments$chr),
                expected_fit_segments$chr
            ) &&
            equal_values(
                fit_segments$startpos,
                expected_fit_segments$startpos
            ) &&
            equal_values(fit_segments$endpos, expected_fit_segments$endpos) &&
            equal_values(
                fit_segments$logRMean,
                expected_fit_segments$logRMean
            ) &&
            equal_values(fit_segments$bafMean, expected_fit_segments$bafMean) &&
            equal_values(fit_segments$nProbes, expected_fit_segments$nProbes),
        paste(sample, "fit segments differ from the joint ASCAT runs.")
    )
    assert(
        sum(fit_segments$nProbes) == heterozygous_count,
        paste(sample, "fit-segment weights do not cover heterozygous probes.")
    )

    message(
        sample,
        ": ",
        nrow(segments),
        " final segments, ",
        nrow(fit_segments),
        " fit segments, ",
        nrow(raw),
        " probes, ",
        heterozygous_count,
        " heterozygous BAF values"
    )
}

message("Validated ", nrow(fits), " samples in ", output_dir)
