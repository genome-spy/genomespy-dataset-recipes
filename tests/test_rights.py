import subprocess
from pathlib import Path

import pytest

from tools.check_new_recipe_rights import check_new_recipe_rights
from tools.rights import has_recognized_decision


@pytest.mark.parametrize(
    "decision",
    [
        "Eligible for GenomeSpy-managed hosting under the conditions above.",
        "Use the authoritative upstream URL.",
        "Use the authoritative immutable upstream URLs.",
        "Local-only: prohibited.",
        "Local-only: unresolved.",
    ],
)
def test_recognizes_documented_rights_decisions(decision: str) -> None:
    assert has_recognized_decision(f"# Rights\n\n## Decision\n\n{decision}\n")


@pytest.mark.parametrize(
    "rights",
    [
        "# Rights\n\nEligible for GenomeSpy-managed hosting.\n",
        "# Rights\n\n## Conditions and decision\n\nLocal-only: unresolved.\n",
        "# Rights\n\n## Decision\n\n**Eligible for GenomeSpy-managed hosting.**\n",
        "# Rights\n\n## Decision\n\nChoose one.\n",
    ],
)
def test_rejects_missing_or_noncanonical_decisions(rights: str) -> None:
    assert not has_recognized_decision(rights)


def git(root: Path, *args: str) -> str:
    """Run Git in a temporary test repository."""

    result = subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def commit(root: Path, message: str) -> str:
    """Commit the test repository and return the commit ID."""

    git(root, "add", ".")
    git(
        root,
        "-c",
        "commit.gpgsign=false",
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.org",
        "commit",
        "-m",
        message,
    )
    return git(root, "rev-parse", "HEAD")


def test_checks_only_recipes_introduced_after_base(tmp_path: Path) -> None:
    git(tmp_path, "init", "--initial-branch=main")
    existing = tmp_path / "recipes" / "existing"
    existing.mkdir(parents=True)
    (existing / "RIGHTS.md").write_text("# No decision\n", encoding="utf-8")
    base = commit(tmp_path, "base")

    added = tmp_path / "recipes" / "added"
    added.mkdir()
    (added / "RIGHTS.md").write_text(
        "# Rights\n\n## Decision\n\n**Eligible for GenomeSpy-managed hosting.**\n",
        encoding="utf-8",
    )
    head = commit(tmp_path, "add recipe")

    assert check_new_recipe_rights(base, head, tmp_path) == [
        "added: RIGHTS.md must have one ## Decision section that starts with a "
        "recognized decision"
    ]


def test_accepts_new_recipe_with_decision(tmp_path: Path) -> None:
    git(tmp_path, "init", "--initial-branch=main")
    recipes = tmp_path / "recipes"
    recipes.mkdir()
    template = recipes / "_template"
    template.mkdir()
    (template / "RIGHTS.md").write_text("# Template\n", encoding="utf-8")
    base = commit(tmp_path, "base")

    added = recipes / "added"
    added.mkdir()
    (added / "RIGHTS.md").write_text(
        "# Rights\n\n## Decision\n\nLocal-only: unresolved.\n", encoding="utf-8"
    )
    head = commit(tmp_path, "add recipe")

    assert check_new_recipe_rights(base, head, tmp_path) == []
