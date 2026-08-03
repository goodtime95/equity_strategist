from equity_strategist.data_providers.yahoo import YahooFinanceProvider
from equity_strategist.services.market_queries import MarketQueryService
from equity_strategist.services.market_series import MarketSeriesService
from equity_strategist.tools.assets import AssetResolver
from equity_strategist.tools.prices import PriceTool


def build_market_query_service() -> MarketQueryService:
    """Build the market query service."""
    provider = YahooFinanceProvider()
    asset_resolver = AssetResolver(provider)
    price_tool = PriceTool(provider)

    return MarketQueryService(
        asset_resolver=asset_resolver,
        price_tool=price_tool,
    )


def build_market_series_service() -> MarketSeriesService:
    """Build the market series service."""
    provider = YahooFinanceProvider()
    asset_resolver = AssetResolver(provider)

    return MarketSeriesService(
        provider=provider,
        asset_resolver=asset_resolver,
    )
