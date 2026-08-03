from equity_strategist.asset_registry.registry import AssetRegistry
from equity_strategist.domain.asset import Asset
from equity_strategist.tools.exceptions import (
    AmbiguousAssetError,
    AssetNotFoundError,
)


class AssetResolver:
    """Resolve a user query into a registered financial asset."""

    def __init__(self, registry: AssetRegistry) -> None:
        self.registry = registry

    def resolve(
        self,
        query: str,
        preferred_currency: str | None = None,
        preferred_exchange: str | None = None,
    ) -> Asset:
        """Return the most relevant registered asset."""
        clean_query = query.strip()

        if not clean_query:
            raise AssetNotFoundError("Asset query cannot be empty")

        assets = self.registry.search(clean_query)

        if preferred_exchange is not None:
            assets = [
                asset
                for asset in assets
                if asset.exchange
                and preferred_exchange.casefold() in asset.exchange.casefold()
            ]

        if preferred_currency is not None:
            assets = [asset for asset in assets if asset.currency == preferred_currency]

        if not assets:
            raise AssetNotFoundError(
                f"No registered asset found for query: {clean_query}"
            )

        if len(assets) == 1:
            return assets[0]

        candidates = ", ".join(
            f"{asset.symbol} ({asset.name or 'Unknown'})" for asset in assets[:5]
        )

        raise AmbiguousAssetError(
            f"Several registered assets match '{clean_query}': {candidates}"
        )
