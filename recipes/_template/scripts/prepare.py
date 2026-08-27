#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0

# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""Replace with a deterministic preparation workflow."""

from pathlib import Path


def main() -> None:
    """Create standard working directories and stop at the template boundary."""

    recipe_dir = Path(__file__).resolve().parents[1]
    for name in ("download", "work", "output"):
        (recipe_dir / name).mkdir(exist_ok=True)
    raise NotImplementedError("Replace the recipe template implementation.")


if __name__ == "__main__":
    main()
