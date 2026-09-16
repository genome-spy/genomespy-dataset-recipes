#!/usr/bin/env python3
"""Require a recognized rights decision for recipes added after a Git revision."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from tools.rights import has_recognized_decision

ROOT = Path(__file__).resolve().parents[1]


def recipe_ids_at_revision(revision: str, root: Path = ROOT) -> set[str]:
    """Return concrete recipe directory names at a Git revision."""

    result = subprocess.run(
        ["git", "ls-tree", "-d", "--name-only", f"{revision}:recipes"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        recipe_id
        for recipe_id in result.stdout.splitlines()
        if recipe_id and recipe_id != "_template"
    }


def read_at_revision(path: str, revision: str, root: Path = ROOT) -> str | None:
    """Return a UTF-8 file from a Git revision, or None when it does not exist."""

    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=root,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8")


def check_new_recipe_rights(
    base: str, head: str = "HEAD", root: Path = ROOT
) -> list[str]:
    """Return errors for new recipes without a recognized rights decision."""

    new_recipe_ids = sorted(
        recipe_ids_at_revision(head, root) - recipe_ids_at_revision(base, root)
    )
    errors: list[str] = []
    for recipe_id in new_recipe_ids:
        relative = f"recipes/{recipe_id}/RIGHTS.md"
        rights = read_at_revision(relative, head, root)
        if rights is None:
            errors.append(f"{recipe_id}: missing RIGHTS.md")
        elif not has_recognized_decision(rights):
            errors.append(
                f"{recipe_id}: RIGHTS.md must have one ## Decision section that "
                "starts with a recognized decision"
            )
    return errors


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="PR base commit")
    parser.add_argument("--head", default="HEAD", help="PR head commit")
    return parser.parse_args()


def main() -> None:
    """Check newly introduced recipes and report contract errors."""

    args = parse_args()
    errors = check_new_recipe_rights(args.base, args.head)
    if errors:
        for error in errors:
            print("ERROR: " + error)
        raise SystemExit(1)
    print("New recipe rights decisions passed.")


if __name__ == "__main__":
    main()
