"""Local preconditions shared by validation and deterministic ranking services."""

from collections.abc import Sequence


def has_ranking_cardinality(asset_count: int) -> bool:
    return asset_count >= 2


def has_unique_references(references: Sequence[str]) -> bool:
    normalized = [reference.strip().casefold() for reference in references]
    return len(normalized) == len(set(normalized))


def ranking_reference_issue(references: Sequence[str]) -> str | None:
    if not has_ranking_cardinality(len(references)):
        return "at least two assets are required for ranking"
    if not has_unique_references(references):
        return "duplicate asset references are not allowed for ranking"
    return None
