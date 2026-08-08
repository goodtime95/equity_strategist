from equity_strategist.asset_registry import (
    build_default_asset_registry,
)
from equity_strategist.data_providers.yahoo import YahooFinanceProvider
from equity_strategist.services.market_queries import MarketQueryService
from equity_strategist.services.market_series import MarketSeriesService
from equity_strategist.services.volatility_analysis import (
    VolatilityAnalysisService,
)
from equity_strategist.tools.assets import AssetResolver
from equity_strategist.tools.prices import PriceTool


def build_market_query_service() -> MarketQueryService:
    """Build the market query service."""
    provider = YahooFinanceProvider()
    registry = build_default_asset_registry()
    asset_resolver = AssetResolver(registry)
    price_tool = PriceTool(provider)

    return MarketQueryService(
        asset_resolver=asset_resolver,
        price_tool=price_tool,
    )


def build_market_series_service() -> MarketSeriesService:
    """Build the market series service."""
    provider = YahooFinanceProvider()
    registry = build_default_asset_registry()
    asset_resolver = AssetResolver(registry)

    return MarketSeriesService(
        provider=provider,
        asset_resolver=asset_resolver,
    )


def build_volatility_analysis_service() -> VolatilityAnalysisService:
    """Build the volatility analysis service."""
    market_series_service = build_market_series_service()

    return VolatilityAnalysisService(
        market_series_service=market_series_service,
    )
