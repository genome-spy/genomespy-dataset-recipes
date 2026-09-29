"""Check the single-sample BRCA MAF contract with small fixtures."""

import gzip

import pytest
from test_python_migration_recipes import load_recipe


@pytest.mark.parametrize(
    "problem", [None, "sample", "position", "allele", "chromosome"]
)
def test_brca_contract_rejects_changed_sample_or_invalid_snv(problem):
    module = load_recipe("maftools-tcga-brca-mutations")
    fields = [
        "Chromosome",
        "Start_Position",
        "End_Position",
        "Reference_Allele",
        "Tumor_Seq_Allele2",
        "Variant_Type",
        "Tumor_Sample_Barcode",
    ]
    row = ["1", "10", "10", "A", "T", "SNP", "SAMPLE"]
    if problem == "sample":
        row[-1] = "OTHER"
    elif problem == "position":
        row[1] = "0"
    elif problem == "allele":
        row[4] = "A"
    elif problem == "chromosome":
        row[0] = "X"
    raw = gzip.compress(("\t".join(fields) + "\n" + "\t".join(row) + "\n").encode())
    expected = {
        "columns": fields,
        "recordCount": 1,
        "sample": "SAMPLE",
        "chromosomes": ["1"],
    }
    if problem is None:
        module.validate_tables({"mutations": raw}, expected)
    else:
        with pytest.raises(ValueError):
            module.validate_tables({"mutations": raw}, expected)
