"""Guard alignment conservation and coordinate conventions during migration."""

import hashlib

import pytest
from test_python_migration_recipes import load_recipe


@pytest.mark.parametrize("problem", [None, "residue", "order", "length", "alphabet"])
def test_p53_alignment_preserves_records_and_residues(problem):
    recipe = load_recipe("uniprot-p53-alignment")
    source = "".join(f">protein{i}\nACD\n" for i in range(34)).encode()
    sequences = [("protein" + str(i), "A-CD") for i in range(34)]
    if problem == "residue":
        sequences[0] = ("protein0", "A-CE")
    elif problem == "order":
        sequences.reverse()
    elif problem == "length":
        sequences[0] = ("protein0", "ACD")
    elif problem == "alphabet":
        sequences[0] = ("protein0", "A-?D")
    aligned = "".join(f">{name}\n{seq}\n" for name, seq in sequences).encode()
    if problem is None:
        recipe.validate_alignment(aligned, source)
    else:
        with pytest.raises(ValueError):
            recipe.validate_alignment(aligned, source)


@pytest.mark.parametrize(
    "problem", [None, "one-based", "chromosome", "outside", "sequence"]
)
def test_tal1_control_uses_one_based_position_with_half_open_interval(problem):
    recipe = load_recipe("ucsc-tal1-hg38-reference")
    sequence = "ACGT"
    metadata = {
        "interval": {"chrom": "chr1", "start0": 100, "end0": 104},
        "positive_control_site": {"chrom": "chr1", "pos1": 102, "ref": "C"},
        "sequence_sha256": hashlib.sha256(sequence.encode()).hexdigest(),
    }
    if problem == "one-based":
        metadata["positive_control_site"]["pos1"] = 101
    elif problem == "chromosome":
        metadata["positive_control_site"]["chrom"] = "chr2"
    elif problem == "outside":
        metadata["positive_control_site"]["pos1"] = 105
    elif problem == "sequence":
        sequence = "ACGA"
    if problem is None:
        recipe.validate_sequence(sequence, metadata)
    else:
        with pytest.raises(ValueError):
            recipe.validate_sequence(sequence, metadata)
