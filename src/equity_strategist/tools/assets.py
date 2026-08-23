import re
import unicodedata

from equity_strategist.asset_registry.registry import AssetRegistry
from equity_strategist.data_providers.base import MarketDataProvider
from equity_strategist.domain.asset import Asset
from equity_strategist.tools.exceptions import (
    AmbiguousAssetError,
    AssetNotFoundError,
)


class AssetResolver:
    """Resolve a user query into a financial asset."""

    def __init__(
        self,
        registry: AssetRegistry,
        fallback_provider: MarketDataProvider | None = None,
    ) -> None:
        self.registry = registry
        self.fallback_provider = fallback_provider

    def resolve(
        self,
        query: str,
        preferred_currency: str | None = None,
        preferred_exchange: str | None = None,
    ) -> Asset:
        """Return the most relevant asset for a user query."""

        clean_query = query.strip()

        if not clean_query:
            raise AssetNotFoundError("Asset query cannot be empty")

        registered_assets = self.registry.search(clean_query)

        registered_assets = self._apply_preferences(
            assets=registered_assets,
            preferred_currency=preferred_currency,
            preferred_exchange=preferred_exchange,
        )

        if registered_assets:
            return self._select_unique_asset(
                query=clean_query,
                assets=registered_assets,
                source="registered",
            )

        if self.fallback_provider is None:
            raise AssetNotFoundError(
                f"No registered asset found for query: {clean_query}"
            )

        fallback_assets = self.fallback_provider.search_assets(clean_query)

        fallback_assets = self._apply_preferences(
            assets=fallback_assets,
            preferred_currency=preferred_currency,
            preferred_exchange=preferred_exchange,
        )

        if not fallback_assets:
            raise AssetNotFoundError(f"No asset found for query: {clean_query}")

        return self._select_external_asset(
            query=clean_query,
            assets=fallback_assets,
        )

    @staticmethod
    def _apply_preferences(
        assets: list[Asset],
        preferred_currency: str | None,
        preferred_exchange: str | None,
    ) -> list[Asset]:
        filtered_assets = assets

        if preferred_exchange is not None:
            filtered_assets = [
                asset
                for asset in filtered_assets
                if asset.exchange
                and preferred_exchange.casefold() in asset.exchange.casefold()
            ]

        if preferred_currency is not None:
            filtered_assets = [
                asset
                for asset in filtered_assets
                if asset.currency == preferred_currency
            ]

        return filtered_assets

    @staticmethod
    def _select_unique_asset(
        query: str,
        assets: list[Asset],
        source: str,
    ) -> Asset:
        if len(assets) == 1:
            return assets[0]

        candidates = ", ".join(
            (f"{asset.symbol} ({asset.name or 'Unknown'})") for asset in assets[:5]
        )

        raise AmbiguousAssetError(
            f"Several {source} assets match '{query}': {candidates}"
        )

    @classmethod
    def _select_external_asset(
        cls,
        query: str,
        assets: list[Asset],
    ) -> Asset:
        if len(assets) == 1:
            return assets[0]

        clean_query = cls._normalize_text(query)

        # Exact ticker match is strong enough to resolve directly.
        exact_symbol_matches = [
            asset
            for asset in assets
            if cls._normalize_text(asset.symbol) == clean_query
        ]

        if len(exact_symbol_matches) == 1:
            return exact_symbol_matches[0]

        scored_assets = [
            (
                cls._external_match_score(
                    query=query,
                    asset=asset,
                    provider_rank=rank,
                ),
                asset,
            )
            for rank, asset in enumerate(assets)
        ]

        scored_assets.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        best_score, best_asset = scored_assets[0]
        second_score = scored_assets[1][0]

        if best_score >= 100 and best_score - second_score >= 5:
            return best_asset

        candidates = ", ".join(
            (f"{asset.symbol} ({asset.name or 'Unknown'})")
            for _, asset in scored_assets[:5]
        )

        raise AmbiguousAssetError(
            f"Several external assets match '{query}': {candidates}"
        )

    @classmethod
    def _external_match_score(
        cls,
        query: str,
        asset: Asset,
        provider_rank: int,
    ) -> int:
        clean_query = cls._normalize_text(query)

        clean_symbol = cls._normalize_text(asset.symbol)

        clean_name = cls._normalize_text(asset.name or "")

        score = 0

        if clean_query == clean_symbol:
            score += 120

        if clean_query == clean_name:
            score += 100

        elif clean_name.startswith(clean_query):
            score += 80

        elif clean_query in clean_name:
            score += 60

        query_tokens = set(clean_query.split())

        name_tokens = set(clean_name.split())

        if query_tokens and query_tokens.issubset(name_tokens):
            score += 20

        secondary_markers = (
            "adr",
            "unsp ad",
            "unsponsored",
            "index",
        )

        if any(marker in clean_name for marker in secondary_markers):
            score -= 30

        # Yahoo Search already returns candidates
        # in relevance order. Use this only as
        # a weak tie-breaker.
        score += max(
            0,
            10 - provider_rank,
        )

        return score

    @staticmethod
    def _normalize_text(
        value: str,
    ) -> str:
        normalized = unicodedata.normalize(
            "NFKD",
            value,
        )

        normalized = "".join(
            char for char in normalized if not unicodedata.combining(char)
        )

        normalized = normalized.casefold()

        normalized = re.sub(
            r"[^a-z0-9]+",
            " ",
            normalized,
        )

        return " ".join(normalized.split())
