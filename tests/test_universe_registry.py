import pytest

from equity_strategist.domain.universe import (
    Universe,
    UniverseType,
)
from equity_strategist.universe_registry.defaults import (
    build_default_universe_registry,
)
from equity_strategist.universe_registry.registry import (
    UniverseRegistry,
)


def build_registry() -> UniverseRegistry:
    return UniverseRegistry(
        [
            Universe(
                name="Luxury Europe",
                universe_type=UniverseType.STATIC,
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
                universe_type=UniverseType.STATIC,
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


def test_static_universe_requires_assets() -> None:
    with pytest.raises(
        ValueError,
        match="static universe requires assets",
    ):
        Universe(
            name="Empty",
            universe_type=UniverseType.STATIC,
            asset_queries=(),
        )


def test_dynamic_universe_requires_provider_identifier() -> None:
    with pytest.raises(
        ValueError,
        match="dynamic universe requires provider identifier",
    ):
        Universe(
            name="CAC 40",
            universe_type=UniverseType.DYNAMIC,
            provider="euronext",
        )


def test_resolve_dynamic_universe() -> None:
    registry = build_default_universe_registry()

    universe = registry.resolve("CAC 40")

    assert universe.name == "CAC 40"
    assert universe.universe_type == UniverseType.DYNAMIC
    assert universe.provider == "euronext"
    assert universe.provider_identifier == "FR0003500008-XPAR"
    assert universe.asset_queries == ()
