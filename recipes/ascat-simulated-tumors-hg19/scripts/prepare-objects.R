#!/usr/bin/env Rscript
# SPDX-License-Identifier: CC0-1.0

# Generate the ASCAT object used by the visualization wrangling scripts.

script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
if (length(script_arg) != 1) {
    stop("Run this script using Rscript.", call. = FALSE)
}

script_path <- normalizePath(sub("^--file=", "", script_arg), mustWork = TRUE)
recipe_dir <- dirname(dirname(script_path))
input_dir <- Sys.getenv("ASCAT_INPUT_DIR", file.path(recipe_dir, "download"))
work_dir <- Sys.getenv("ASCAT_WORK_DIR", file.path(recipe_dir, "work"))
dir.create(work_dir, recursive = TRUE, showWarnings = FALSE)
input_dir <- normalizePath(input_dir, mustWork = TRUE)
work_dir <- normalizePath(work_dir, mustWork = TRUE)
previous_dir <- setwd(work_dir)
on.exit(setwd(previous_dir))

expected_sha256 <- c(
    "Tumor_LogR.txt" = "6a01557a81bc478a73bb7b6c92ba9249b2a700eaf47a62cf45ff5e2be54574d2",
    "Tumor_BAF.txt" = "bcb9ddbea4554ccba56dfee7e703bb715e1a256070f18a34a896ed8998e4ef1d",
    "Germline_LogR.txt" = "671be8a6975d69a662ebfa8f433cf7407463a79c34ccf831805fb64335ad8771",
    "Germline_BAF.txt" = "c66161a8118d3be45ef1f007d4b342c5a5d509a302b964e97814395f2aa790e6",
    "GC_example.txt" = "08a9c9c5f464da2c0ca9e3d134e8dfcfc9d6702c855b977437328edee9221d19",
    "RT_example.txt" = "6bf3c7efa36076c723b41fc2a754d2f1e97b9bf188606309e548d383edd22500"
)
input_paths <- file.path(input_dir, names(expected_sha256))
missing_files <- names(expected_sha256)[!file.exists(input_paths)]
if (length(missing_files) > 0) {
    stop("Missing pinned input: ", missing_files[1], call. = FALSE)
}

actual_sha256 <- unname(tools::sha256sum(input_paths))
mismatched_files <- names(expected_sha256)[
    is.na(actual_sha256) | actual_sha256 != unname(expected_sha256)
]
if (length(mismatched_files) > 0) {
    stop(
        "SHA-256 mismatch for pinned input: ",
        mismatched_files[1],
        call. = FALSE
    )
}

suppressPackageStartupMessages(library(ASCAT))
ascat.bc <- ascat.loadData(
    Tumor_LogR_file = file.path(input_dir, "Tumor_LogR.txt"),
    Tumor_BAF_file = file.path(input_dir, "Tumor_BAF.txt"),
    Germline_LogR_file = file.path(input_dir, "Germline_LogR.txt"),
    Germline_BAF_file = file.path(input_dir, "Germline_BAF.txt"),
    gender = rep("XX", 100),
    genomeVersion = "hg19"
)
ascat.bc <- ascat.correctLogR(
    ascat.bc,
    GCcontentfile = file.path(input_dir, "GC_example.txt"),
    replictimingfile = file.path(input_dir, "RT_example.txt")
)
ascat.bc <- ascat.aspcf(ascat.bc, out.dir = work_dir)
ascat.output <- ascat.runAscat(ascat.bc, write_segments = FALSE)
QC <- ascat.metrics(ascat.bc, ascat.output)
save(ascat.bc, ascat.output, QC, file = file.path(work_dir, "ASCAT_objects.Rdata"))
