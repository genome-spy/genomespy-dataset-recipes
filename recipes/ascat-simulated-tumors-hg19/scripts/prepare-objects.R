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

required_files <- c(
    "Tumor_LogR.txt",
    "Tumor_BAF.txt",
    "Germline_LogR.txt",
    "Germline_BAF.txt",
    "GC_example.txt",
    "RT_example.txt"
)
for (filename in required_files) {
    if (!file.exists(file.path(input_dir, filename))) {
        stop("Missing pinned input: ", filename, call. = FALSE)
    }
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
