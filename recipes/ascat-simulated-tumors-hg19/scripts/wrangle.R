#!/usr/bin/env Rscript
# SPDX-License-Identifier: CC0-1.0

# Convert the saved ASCAT example objects into flat TSV relations used by the
# GenomeSpy ASCAT examples.

default_samples <- c(
    "S17",
    "S36",
    "S54",
    "S64",
    "S77",
    "S84",
    "S96",
    "S97",
    "S100"
)

# Preserve segmented values exactly enough to reproduce ASCAT's distance
# matrix. Raw values are explicitly rounded below.
options(digits = 17)

get_script_path <- function() {
    file_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
    if (length(file_arg) != 1) {
        stop("Run this script using Rscript.", call. = FALSE)
    }

    normalizePath(sub("^--file=", "", file_arg), mustWork = TRUE)
}

write_tsv <- function(data, path) {
    output <- if (endsWith(path, ".gz")) gzfile(path, "wt") else path
    if (inherits(output, "connection")) {
        on.exit(close(output))
    }

    write.table(
        data,
        file = output,
        sep = "\t",
        quote = FALSE,
        row.names = FALSE,
        col.names = TRUE,
        na = ""
    )
}

write_tsv_variants <- function(data, path) {
    write_tsv(data, path)
    status <- system2("gzip", c("-n", "-f", "-k", shQuote(path)))
    if (status != 0) {
        stop("gzip failed for ", path, call. = FALSE)
    }
}

align_named_values <- function(values, value_names, snp_names, label) {
    indices <- match(snp_names, value_names)
    if (anyNA(indices)) {
        stop(label, " is missing SNPs required by SNPpos.", call. = FALSE)
    }

    as.numeric(values[indices])
}

assign_segments <- function(snp_positions, segments, sample) {
    segment_id <- integer(nrow(snp_positions))

    for (i in seq_len(nrow(segments))) {
        in_segment <-
            snp_positions$chr == as.character(segments$chr[i]) &
            snp_positions$pos >= segments$startpos[i] &
            snp_positions$pos <= segments$endpos[i]

        if (any(segment_id[in_segment] != 0)) {
            stop(sample, " has overlapping segment intervals.", call. = FALSE)
        }

        segment_id[in_segment] <- i
    }

    if (any(segment_id == 0)) {
        stop(
            sample,
            " has ",
            sum(segment_id == 0),
            " SNPs outside the final ASCAT segments.",
            call. = FALSE
        )
    }

    segment_id
}

segment_mean <- function(values, segment_id, segment_count) {
    vapply(
        seq_len(segment_count),
        function(i) mean(values[segment_id == i], na.rm = TRUE),
        numeric(1)
    )
}

make_fit_segments <- function(ascat_bc, sample, sample_index) {
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

wrangle_sample <- function(ascat_bc, ascat_output, sample, output_dir) {
    sample_index <- match(sample, ascat_bc$samples)
    if (is.na(sample_index)) {
        stop("Unknown ASCAT sample: ", sample, call. = FALSE)
    }

    snp_positions <- data.frame(
        SNP = rownames(ascat_bc$SNPpos),
        chr = as.character(ascat_bc$SNPpos$chrs),
        pos = as.integer(ascat_bc$SNPpos$pos),
        stringsAsFactors = FALSE
    )

    segments <- ascat_output$segments[
        ascat_output$segments$sample == sample,
        c("sample", "chr", "startpos", "endpos", "nMajor", "nMinor")
    ]
    rownames(segments) <- NULL

    if (nrow(segments) == 0) {
        stop("ASCAT has no final segments for ", sample, ".", call. = FALSE)
    }

    segment_id <- assign_segments(snp_positions, segments, sample)
    snp_names <- snp_positions$SNP

    segmented_logr <- align_named_values(
        ascat_bc$Tumor_LogR_segmented[, sample_index],
        rownames(ascat_bc$Tumor_LogR_segmented),
        snp_names,
        paste0(sample, " segmented LogR")
    )

    segmented_baf_values <- ascat_bc$Tumor_BAF_segmented[[sample_index]][, 1]
    segmented_baf <- rep(NA_real_, length(snp_names))
    segmented_baf[match(names(segmented_baf_values), snp_names)] <-
        as.numeric(segmented_baf_values)

    segments$logRMean <- round(
        segment_mean(segmented_logr, segment_id, nrow(segments)),
        3
    )
    segments$bafMean <- round(
        segment_mean(segmented_baf, segment_id, nrow(segments)),
        3
    )
    segments$nProbes <- tabulate(segment_id, nbins = nrow(segments))

    raw_logr <- align_named_values(
        ascat_bc$Tumor_LogR[, sample_index],
        rownames(ascat_bc$Tumor_LogR),
        snp_names,
        paste0(sample, " raw LogR")
    )
    raw_baf <- align_named_values(
        ascat_bc$Tumor_BAF[, sample_index],
        rownames(ascat_bc$Tumor_BAF),
        snp_names,
        paste0(sample, " raw BAF")
    )

    # Tumor_BAF contains values at every probe. Keep BAF only at loci retained
    # by ASPCF as germline-heterozygous SNPs, matching the existing S96 TSV.
    raw_baf[is.na(segmented_baf)] <- NA_real_
    raw_logr <- signif(raw_logr, digits = 3)
    raw_baf <- signif(raw_baf, digits = 3)

    raw <- data.frame(
        snp_positions,
        logR = raw_logr,
        baf = raw_baf,
        stringsAsFactors = FALSE
    )
    fit_segments <- make_fit_segments(ascat_bc, sample, sample_index)
    sample_dir <- file.path(output_dir, "samples", sample)
    dir.create(sample_dir, recursive = TRUE, showWarnings = FALSE)

    write_tsv_variants(
        segments,
        file.path(sample_dir, "segments.tsv")
    )
    write_tsv_variants(
        fit_segments,
        file.path(sample_dir, "fit-segments.tsv")
    )
    write_tsv_variants(
        raw,
        file.path(sample_dir, "raw.tsv")
    )

    data.frame(
        sample = sample,
        rho = unname(ascat_output$aberrantcellfraction[sample]),
        psi = unname(ascat_output$psi[sample]),
        ploidy = unname(ascat_output$ploidy[sample]),
        goodnessOfFit = unname(ascat_output$goodnessOfFit[sample]),
        stringsAsFactors = FALSE
    )
}

script_path <- get_script_path()
recipe_dir <- dirname(dirname(script_path))
data_dir <- Sys.getenv("ASCAT_DATA_DIR", file.path(recipe_dir, "download"))
output_dir <- Sys.getenv("ASCAT_OUTPUT_DIR", file.path(recipe_dir, "output"))
samples <- commandArgs(trailingOnly = TRUE)
if (length(samples) == 0) {
    samples <- default_samples
}

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

objects <- new.env(parent = baseenv())
load(file.path(data_dir, "ASCAT_objects.Rdata"), envir = objects)

required_objects <- c("ascat.bc", "ascat.output")
if (!all(required_objects %in% ls(objects))) {
    stop(
        "ASCAT_objects.Rdata must contain ascat.bc and ascat.output.",
        call. = FALSE
    )
}

fits <- do.call(
    rbind,
    lapply(
        samples,
        function(sample) {
            message("Wrangling ", sample)
            wrangle_sample(
                objects$ascat.bc,
                objects$ascat.output,
                sample,
                output_dir
            )
        }
    )
)

write_tsv_variants(fits, file.path(output_dir, "fits.tsv"))
message("Wrote ", length(samples) * 6 + 2, " files to ", output_dir)
