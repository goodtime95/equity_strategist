from equity_strategist.data_providers.yahoo import YahooFinanceProvider
from equity_strategist.services.market_queries import MarketQueryService
from equity_strategist.tools.assets import AssetResolver
from equity_strategist.tools.prices import PriceTool


def build_market_query_service() -> MarketQueryService:
    """Build the application with its concrete dependencies."""
    provider = YahooFinanceProvider()

    asset_resolver = AssetResolver(provider)
    price_tool = PriceTool(provider)

    return MarketQueryService(
        asset_resolver=asset_resolver,
        price_tool=price_tool,
    )
