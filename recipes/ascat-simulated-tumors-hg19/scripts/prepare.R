#!/usr/bin/env Rscript
# SPDX-License-Identifier: CC0-1.0

# Run the complete ASCAT example-data workflow from recipe-relative paths.

file_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
if (length(file_arg) != 1) {
    stop("Run this script using Rscript.", call. = FALSE)
}

script_path <- normalizePath(sub("^--file=", "", file_arg), mustWork = TRUE)
scripts_dir <- dirname(script_path)
recipe_dir <- dirname(scripts_dir)

Sys.setenv(
    ASCAT_INPUT_DIR = file.path(recipe_dir, "download"),
    ASCAT_WORK_DIR = file.path(recipe_dir, "work"),
    ASCAT_DATA_DIR = file.path(recipe_dir, "work"),
    ASCAT_OUTPUT_DIR = file.path(recipe_dir, "output")
)

run_script <- function(filename) {
    message("Running ", filename)
    status <- system2(
        file.path(R.home("bin"), "Rscript"),
        file.path(scripts_dir, filename)
    )
    if (status != 0) {
        stop(filename, " failed with status ", status, call. = FALSE)
    }
}

run_script("prepare-objects.R")
run_script("wrangle.R")
run_script("validate.R")

if (Sys.getenv("ASCAT_SOURCE_DIR") != "") {
    run_script("compare-distances.R")
}
