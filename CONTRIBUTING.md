# Contributing

Keep changes small and recipe-focused. Start with the
[recipe guide](docs/recipe-guide.md) and copy `recipes/_template/` for a new
dataset.

Before opening a change:

1. Confirm that no downloaded or generated dataset artifact is tracked.
2. Run the recipe from its documented pinned source.
3. Run its scientific validation and inspect its local GenomeSpy spec when one
   exists.
4. Update compact provenance without embedding source records or local paths.
5. Run `uv run python tools/check_repo.py`, Ruff, mypy, and pytest.
6. State unresolved source, coordinate, validation, or redistribution questions
   honestly.

Contributions to CC0-covered paths represent that the contributor controls the
applicable rights and applies the dedication described in
[LICENSE-SCOPE.md](LICENSE-SCOPE.md). Do not contribute copied or closely
adapted third-party source text.

Record every recipe's hosting assessment in `RIGHTS.md`. A request that includes
publication may perform the rights review and upload in the same workflow when
the evidence satisfies [the protocol](docs/rights-and-publication.md); no second
approval step is required.
