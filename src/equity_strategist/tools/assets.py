from equity_strategist.data_providers.base import MarketDataProvider
from equity_strategist.domain.models import Asset
from equity_strategist.tools.exceptions import (
    AmbiguousAssetError,
    AssetNotFoundError,
)


class AssetResolver:
    """Resolve a company name or ticker into a financial asset."""

    def __init__(self, provider: MarketDataProvider) -> None:
        self.provider = provider

    def resolve(
        self,
        query: str,
        preferred_currency: str | None = None,
        preferred_exchange: str | None = None,
    ) -> Asset:
        """Return the most relevant asset matching the query."""
        clean_query = query.strip()

        if not clean_query:
            raise AssetNotFoundError("Asset query cannot be empty")

        assets = self.provider.search_assets(clean_query)

        if not assets:
            raise AssetNotFoundError(f"No asset found for query: {clean_query}")

        exact_symbol_matches = [
            asset
            for asset in assets
            if asset.symbol.casefold() == clean_query.casefold()
        ]

        if len(exact_symbol_matches) == 1:
            return exact_symbol_matches[0]

        exact_name_matches = [
            asset
            for asset in assets
            if asset.name and asset.name.casefold() == clean_query.casefold()
        ]

        if len(exact_name_matches) == 1:
            return exact_name_matches[0]

        if preferred_exchange is not None:
            exchange_matches = [
                asset
                for asset in assets
                if asset.exchange
                and preferred_exchange.casefold() in asset.exchange.casefold()
            ]

            if len(exchange_matches) == 1:
                return exchange_matches[0]

            if exchange_matches:
                assets = exchange_matches

        if preferred_currency is not None:
            currency_matches = [
                asset for asset in assets if asset.currency == preferred_currency
            ]

            if len(currency_matches) == 1:
                return currency_matches[0]

            if currency_matches:
                assets = currency_matches

        if len(assets) == 1:
            return assets[0]

        candidates = ", ".join(
            f"{asset.symbol} ({asset.name or 'Unknown'})" for asset in assets[:5]
        )

        raise AmbiguousAssetError(f"Several assets match '{clean_query}': {candidates}")
