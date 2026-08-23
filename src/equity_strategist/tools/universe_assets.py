from equity_strategist.domain.asset import Asset
from equity_strategist.domain.universe_constituent import (
    UniverseConstituent,
)
from equity_strategist.tools.assets import AssetResolver
from equity_strategist.tools.exceptions import (
    AmbiguousAssetError,
    AssetNotFoundError,
)


class UniverseAssetResolver:
    """Resolve universe constituents into usable primary-listing assets."""

    def __init__(
        self,
        asset_resolver: AssetResolver,
    ) -> None:
        self.asset_resolver = asset_resolver

    def resolve(
        self,
        constituent: UniverseConstituent,
    ) -> Asset:
        queries = self._build_queries(constituent)

        # First try the universe metadata as a preference.
        if constituent.exchange is not None:
            for query in queries:
                try:
                    return self.asset_resolver.resolve(
                        query=query,
                        preferred_exchange=constituent.exchange,
                    )
                except (
                    AssetNotFoundError,
                    AmbiguousAssetError,
                ):
                    continue

        # Then retry without forcing the exchange.
        #
        # Universe membership does not imply that the
        # primary listing is on the universe's local exchange.
        for query in queries:
            try:
                return self.asset_resolver.resolve(
                    query=query,
                )
            except (
                AssetNotFoundError,
                AmbiguousAssetError,
            ):
                continue

        raise AssetNotFoundError(
            f"Unable to resolve universe constituent: {constituent.name}"
        )

    def resolve_many(
        self,
        constituents: tuple[UniverseConstituent, ...],
    ) -> tuple[Asset, ...]:
        return tuple(self.resolve(constituent) for constituent in constituents)

    @staticmethod
    def _build_queries(
        constituent: UniverseConstituent,
    ) -> tuple[str, ...]:
        queries = []

        if constituent.isin:
            queries.append(constituent.isin)

        if constituent.provider_symbol:
            queries.append(constituent.provider_symbol)

        queries.append(constituent.name)

        return tuple(queries)
