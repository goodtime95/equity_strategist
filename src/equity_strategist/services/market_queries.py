from datetime import date

from equity_strategist.domain.results import PriceOnDateResult
from equity_strategist.tools.assets import AssetResolver
from equity_strategist.tools.prices import PriceTool


class MarketQueryService:
    """Coordinate market-data tools to answer user-level queries."""

    def __init__(
        self,
        asset_resolver: AssetResolver,
        price_tool: PriceTool,
    ) -> None:
        self.asset_resolver = asset_resolver
        self.price_tool = price_tool

    def get_price_on_date(
        self,
        asset_query: str,
        target_date: date,
        preferred_exchange: str | None = None,
        preferred_currency: str | None = None,
        use_adjusted_close: bool = True,
    ) -> PriceOnDateResult:
        """Resolve an asset and return its price for a requested date."""
        asset = self.asset_resolver.resolve(
            query=asset_query,
            preferred_exchange=preferred_exchange,
            preferred_currency=preferred_currency,
        )

        return self.price_tool.get_price_on_date(
            asset=asset,
            target_date=target_date,
            use_adjusted_close=use_adjusted_close,
        )
