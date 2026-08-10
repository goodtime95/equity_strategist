from equity_strategist.domain.universe import UniverseType
from equity_strategist.universe_providers.protocol import (
    UniverseProvider,
)
from equity_strategist.universe_registry.registry import (
    UniverseRegistry,
)


class UniverseConstituentService:
    """Resolve named universes into asset queries."""

    def __init__(
        self,
        universe_registry: UniverseRegistry,
        universe_provider: UniverseProvider,
    ) -> None:
        self.universe_registry = universe_registry
        self.universe_provider = universe_provider

    def get_constituents(
        self,
        universe_query: str,
    ) -> tuple[str, ...]:
        universe = self.universe_registry.resolve(universe_query)

        if universe.universe_type == UniverseType.STATIC:
            return universe.asset_queries

        if universe.universe_type == UniverseType.DYNAMIC:
            if universe.provider_identifier is None:
                raise ValueError("dynamic universe requires provider identifier")

            constituents = self.universe_provider.get_constituents(
                universe.provider_identifier
            )

            if not constituents:
                raise ValueError(f"no constituents found for {universe.name}")

            return constituents

        raise ValueError(f"unsupported universe type: {universe.universe_type}")
