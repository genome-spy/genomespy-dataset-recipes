"""Parse the canonical decision from a recipe rights record."""

from __future__ import annotations

import re

DECISION_HEADING = re.compile(r"^##[ \t]+Decision[ \t]*$", re.MULTILINE)
NEXT_HEADING = re.compile(r"^#{1,6}[ \t]+", re.MULTILINE)
ELIGIBLE_DECISION = re.compile(
    r"^Eligible for GenomeSpy-managed hosting(?:\.| under(?:\s|$))", re.IGNORECASE
)
UPSTREAM_DECISION = re.compile(
    r"^Use the authoritative(?: immutable)? upstream URLs?(?:\.|\s|$)",
    re.IGNORECASE,
)
LOCAL_DECISION = re.compile(
    r"^Local-only: (?:prohibited|unresolved)(?:\.|\s|$)", re.IGNORECASE
)


def decision_text(rights: str) -> str | None:
    """Return the Decision section text when it has one unambiguous heading."""

    headings = list(DECISION_HEADING.finditer(rights))
    if len(headings) != 1:
        return None

    section = rights[headings[0].end() :]
    next_heading = NEXT_HEADING.search(section)
    if next_heading:
        section = section[: next_heading.start()]
    return section.lstrip()


def hosting_is_eligible(rights: str) -> bool:
    """Return whether the Decision section starts with the hosting decision."""

    decision = decision_text(rights)
    return decision is not None and ELIGIBLE_DECISION.match(decision) is not None


def has_recognized_decision(rights: str) -> bool:
    """Return whether the rights record starts with a documented decision."""

    decision = decision_text(rights)
    if decision is None:
        return False
    return any(
        pattern.match(decision) is not None
        for pattern in (ELIGIBLE_DECISION, UPSTREAM_DECISION, LOCAL_DECISION)
    )
