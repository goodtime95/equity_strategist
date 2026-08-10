import pytest

from equity_strategist.domain.universe import Universe
from equity_strategist.universe_registry.registry import (
    UniverseRegistry,
)


def build_registry() -> UniverseRegistry:
    return UniverseRegistry(
        [
            Universe(
                name="Luxury Europe",
                asset_queries=(
                    "LVMH",
                    "Hermès",
                ),
                aliases=(
                    "Luxury",
                    "European Luxury",
                ),
            ),
            Universe(
                name="US Tech",
                asset_queries=(
                    "Nvidia",
                    "ASML",
                ),
                aliases=("Technology US",),
            ),
        ]
    )


def test_resolve_universe_by_name() -> None:
    universe = build_registry().resolve("Luxury Europe")

    assert universe.name == "Luxury Europe"
    assert universe.asset_queries == (
        "LVMH",
        "Hermès",
    )


def test_resolve_universe_by_alias() -> None:
    universe = build_registry().resolve("luxury")

    assert universe.name == "Luxury Europe"


def test_unknown_universe_raises() -> None:
    with pytest.raises(
        ValueError,
        match="unknown universe",
    ):
        build_registry().resolve("Unknown Universe")


def test_universe_requires_assets() -> None:
    with pytest.raises(
        ValueError,
        match="at least one asset",
    ):
        Universe(
            name="Empty",
            asset_queries=(),
        )
