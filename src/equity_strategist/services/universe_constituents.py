from equity_strategist.domain.universe import UniverseType
from equity_strategist.domain.universe_constituent import (
    UniverseConstituent,
)
from equity_strategist.universe_providers.protocol import (
    UniverseProvider,
)
from equity_strategist.universe_registry.registry import (
    UniverseRegistry,
)


class UniverseConstituentService:
    """Resolve named universes into structured constituents."""

    def __init__(
        self,
        universe_registry: UniverseRegistry,
        universe_providers: dict[str, UniverseProvider],
    ) -> None:
        self.universe_registry = universe_registry
        self.universe_providers = universe_providers

    def get_constituents(
        self,
        universe_query: str,
    ) -> tuple[UniverseConstituent, ...]:
        universe = self.universe_registry.resolve(universe_query)

        if universe.universe_type == UniverseType.STATIC:
            return tuple(
                UniverseConstituent(
                    name=asset_query,
                )
                for asset_query in universe.asset_queries
            )

        if universe.universe_type == UniverseType.DYNAMIC:
            if universe.provider is None:
                raise ValueError("dynamic universe requires provider")

            if universe.provider_identifier is None:
                raise ValueError("dynamic universe requires provider identifier")

            try:
                provider = self.universe_providers[universe.provider]
            except KeyError as exc:
                raise ValueError(
                    f"unknown universe provider: {universe.provider}"
                ) from exc

            constituents = provider.get_constituents(universe.provider_identifier)

            if not constituents:
                raise ValueError(f"no constituents found for {universe.name}")

            return constituents

        raise ValueError(f"unsupported universe type: {universe.universe_type}")
