from equity_strategist.domain.universe import (
    Universe,
    UniverseType,
)
from equity_strategist.universe_registry.registry import (
    UniverseRegistry,
)

DEFAULT_UNIVERSES = [
    Universe(
        name="Luxury Europe",
        universe_type=UniverseType.STATIC,
        asset_queries=(
            "LVMH",
            "Hermès",
        ),
        aliases=(
            "European Luxury",
            "Luxury",
        ),
    ),
    Universe(
        name="CAC 40",
        universe_type=UniverseType.DYNAMIC,
        provider="euronext",
        provider_identifier="FR0003500008-XPAR",
        aliases=(
            "CAC40",
            "CAC",
        ),
    ),
]


def build_default_universe_registry() -> UniverseRegistry:
    return UniverseRegistry(
        universes=DEFAULT_UNIVERSES,
    )
