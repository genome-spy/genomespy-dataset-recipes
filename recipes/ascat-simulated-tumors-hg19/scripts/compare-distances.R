#!/usr/bin/env Rscript
# SPDX-License-Identifier: CC0-1.0

# Compare the GenomeSpy demo objective, evaluated from the private fit TSVs,
# with the distance matrices saved by ASCAT R v3.2.0.

samples <- c(
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
gamma <- 0.55

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
        check.names = FALSE,
        stringsAsFactors = FALSE
    )
}

calculate_surfaces <- function(segments) {
    segments <- segments[segments$chr != "X", ]
    psi_values <- seq(1, 6, 0.05)
    rho_values <- seq(0.1, 1.05, 0.01)
    fixed <- matrix(nrow = length(psi_values), ncol = length(rho_values))
    dynamic <- matrix(nrow = length(psi_values), ncol = length(rho_values))
    n_a_selected <- matrix(
        FALSE,
        nrow = length(psi_values),
        ncol = length(rho_values)
    )
    weight <- segments$nProbes * ifelse(segments$bafMean == 0.5, 0.05, 1)

    for (i in seq_along(psi_values)) {
        psi <- psi_values[i]
        for (j in seq_along(rho_values)) {
            rho <- rho_values[j]
            abundance <-
                2^(segments$logRMean / gamma) *
                (2 * (1 - rho) + rho * psi)
            n_a <-
                (rho - 1 + (1 - segments$bafMean) * abundance) / rho
            n_b <- (rho - 1 + segments$bafMean * abundance) / rho
            error_a <- (n_a - pmax(round(n_a), 0))^2
            error_b <- (n_b - pmax(round(n_b), 0))^2
            choose_a <- sum(n_a, na.rm = TRUE) < sum(n_b, na.rm = TRUE)
            selected_error <- if (choose_a) error_a else error_b

            fixed[i, j] <- sum(error_b * weight, na.rm = TRUE)
            dynamic[i, j] <- sum(selected_error * weight, na.rm = TRUE)
            n_a_selected[i, j] <- choose_a
        }
    }

    list(fixed = fixed, dynamic = dynamic, n_a_selected = n_a_selected)
}

script_path <- get_script_path()
recipe_dir <- dirname(dirname(script_path))
data_dir <- Sys.getenv("ASCAT_DATA_DIR", file.path(recipe_dir, "download"))
output_dir <- Sys.getenv("ASCAT_OUTPUT_DIR", file.path(recipe_dir, "output"))
ascat_source_dir <- Sys.getenv("ASCAT_SOURCE_DIR")
if (ascat_source_dir == "") {
    stop("ASCAT_SOURCE_DIR must identify a pinned ASCAT checkout.", call. = FALSE)
}
objects <- new.env(parent = baseenv())
load(file.path(data_dir, "ASCAT_objects.Rdata"), envir = objects)
source(
    file.path(
        ascat_source_dir,
        "ASCAT",
        "R",
        "ascat.runAscat.R"
    )
)

results <- do.call(
    rbind,
    lapply(
        samples,
        function(sample) {
            segments <- read_tsv(
                file.path(
                    output_dir, "samples", sample, "fit-segments.tsv"
                )
            )
            surfaces <- calculate_surfaces(segments)
            sample_index <- match(sample, objects$ascat.bc$samples)
            baf <- objects$ascat.bc$Tumor_BAF_segmented[[sample_index]]
            probe_names <- rownames(baf)
            positions <- objects$ascat.bc$SNPpos[probe_names, , drop = FALSE]
            autosomal <- !(
                positions$chrs %in% objects$ascat.bc$sexchromosomes
            )
            reference_segments <- make_segments(
                objects$ascat.bc$Tumor_LogR_segmented[
                    probe_names[autosomal],
                    sample_index
                ],
                baf[autosomal, 1]
            )
            reference <- create_distance_matrix(reference_segments, gamma)
            difference <- surfaces$dynamic - reference
            fixed_difference <- surfaces$fixed - reference

            data.frame(
                sample = sample,
                referenceCorrelation = cor(
                    log10(as.vector(surfaces$dynamic)),
                    log10(as.vector(reference))
                ),
                maximumAbsoluteDifference = max(abs(difference)),
                maximumRelativeDifference = max(
                    abs(difference) / pmax(abs(reference), 1e-12)
                ),
                fixedMinorCorrelation = cor(
                    log10(as.vector(surfaces$fixed)),
                    log10(as.vector(reference))
                ),
                fixedMinorMaximumRelativeDifference = max(
                    abs(fixed_difference) / pmax(abs(reference), 1e-12)
                ),
                nACandidateFraction = mean(surfaces$n_a_selected),
                stringsAsFactors = FALSE
            )
        }
    )
)

options(digits = 8)
write.table(
    results,
    file = file.path(output_dir, "distance_comparison.tsv"),
    row.names = FALSE,
    quote = FALSE,
    sep = "\t"
)
print(results, row.names = FALSE)
