from equity_strategist.data_providers.base import MarketDataProvider
from equity_strategist.domain.asset import Asset
from equity_strategist.domain.universe_constituent import (
    UniverseConstituent,
)
from equity_strategist.tools.assets import AssetResolver
from equity_strategist.tools.exceptions import AssetNotFoundError


class UniverseAssetResolver:
    """Resolve universe constituents into usable Assets."""

    def __init__(
        self,
        asset_resolver: AssetResolver,
        market_data_provider: MarketDataProvider,
    ) -> None:
        self.asset_resolver = asset_resolver
        self.market_data_provider = market_data_provider

    def resolve(
        self,
        constituent: UniverseConstituent,
    ) -> Asset:
        asset = self._resolve_registered(constituent)

        if asset is not None:
            return asset

        asset = self._resolve_from_provider(constituent)

        if asset is not None:
            return asset

        raise AssetNotFoundError(
            f"Unable to resolve universe constituent: {constituent.name}"
        )

    def resolve_many(
        self,
        constituents: tuple[UniverseConstituent, ...],
    ) -> tuple[Asset, ...]:
        return tuple(self.resolve(constituent) for constituent in constituents)

    def _resolve_registered(
        self,
        constituent: UniverseConstituent,
    ) -> Asset | None:
        queries = []

        if constituent.isin:
            queries.append(constituent.isin)

        if constituent.provider_symbol:
            queries.append(constituent.provider_symbol)

        queries.append(constituent.name)

        for query in queries:
            try:
                return self.asset_resolver.resolve(
                    query=query,
                    preferred_exchange=constituent.exchange,
                )
            except AssetNotFoundError:
                continue

        return None

    def _resolve_from_provider(
        self,
        constituent: UniverseConstituent,
    ) -> Asset | None:
        candidates = self.market_data_provider.search_assets(constituent.name)

        if constituent.exchange is not None:
            exchange_matches = [
                asset
                for asset in candidates
                if asset.exchange
                and constituent.exchange.casefold() in asset.exchange.casefold()
            ]

            if len(exchange_matches) == 1:
                return exchange_matches[0]

        if len(candidates) == 1:
            return candidates[0]

        return None
