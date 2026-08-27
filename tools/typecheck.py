#!/usr/bin/env python3
"""Type-check repository tools and recipe Python scripts without name clashes."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_mypy(*paths: Path) -> None:
    """Run mypy for the supplied paths from the repository root."""

    subprocess.run(
        ["mypy", *(str(path.relative_to(ROOT)) for path in paths)],
        cwd=ROOT,
        check=True,
    )


def main() -> None:
    """Check tools together and each identically named recipe script alone."""

    run_mypy(ROOT / "tools")
    scripts = sorted((ROOT / "recipes").glob("*/scripts/*.py"))
    for script in scripts:
        run_mypy(script)


if __name__ == "__main__":
    main()
