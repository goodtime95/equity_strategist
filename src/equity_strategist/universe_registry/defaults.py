from equity_strategist.domain.universe import Universe
from equity_strategist.universe_registry.registry import (
    UniverseRegistry,
)

DEFAULT_UNIVERSES = [
    Universe(
        name="Luxury Europe",
        asset_queries=(
            "LVMH",
            "Hermès",
        ),
        aliases=(
            "European Luxury",
            "Luxury",
        ),
    ),
]


def build_default_universe_registry() -> UniverseRegistry:
    return UniverseRegistry(
        universes=DEFAULT_UNIVERSES,
    )
