from equity_strategist.asset_registry import (
    build_default_asset_registry,
)
from equity_strategist.data_providers.yahoo import YahooFinanceProvider
from equity_strategist.services.correlation_analysis import (
    CorrelationAnalysisService,
)
from equity_strategist.services.drawdown_analysis import (
    DrawdownAnalysisService,
)
from equity_strategist.services.market_dataset import (
    MarketDatasetService,
)
from equity_strategist.services.market_queries import MarketQueryService
from equity_strategist.services.market_series import MarketSeriesService
from equity_strategist.services.performance_analysis import (
    PerformanceAnalysisService,
)
from equity_strategist.services.ranking_analysis import (
    RankingAnalysisService,
)
from equity_strategist.services.volatility_analysis import (
    VolatilityAnalysisService,
)
from equity_strategist.strategists.equity_strategist import (
    EquityStrategist,
)
from equity_strategist.strategists.executor import EquityExecutor
from equity_strategist.strategists.planner import EquityPlanner
from equity_strategist.tools.assets import AssetResolver
from equity_strategist.tools.prices import PriceTool
from equity_strategist.understanding.rule_based import (
    RuleBasedUnderstanding,
)
from equity_strategist.universe_registry import (
    build_default_universe_registry,
)


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
    market_dataset_service = build_market_dataset_service()

    return VolatilityAnalysisService(
        market_dataset_service=market_dataset_service,
    )


def build_market_dataset_service() -> MarketDatasetService:
    """Build the market dataset service."""
    market_series_service = build_market_series_service()

    return MarketDatasetService(
        market_series_service=market_series_service,
    )


def build_equity_strategist() -> EquityStrategist:
    """Build the deterministic Equity Strategist pipeline."""
    planner = EquityPlanner()
    universe_registry = build_default_universe_registry()

    executor = EquityExecutor(
        volatility_analysis_service=(build_volatility_analysis_service()),
        performance_analysis_service=(build_performance_analysis_service()),
        correlation_analysis_service=(build_correlation_analysis_service()),
        drawdown_analysis_service=(build_drawdown_analysis_service()),
        ranking_analysis_service=(build_ranking_analysis_service()),
        market_query_service=build_market_query_service(),
        universe_registry=universe_registry,
    )

    return EquityStrategist(
        planner=planner,
        executor=executor,
        understanding=RuleBasedUnderstanding(
            universe_registry=universe_registry,
        ),
    )


def build_performance_analysis_service() -> PerformanceAnalysisService:
    market_dataset_service = build_market_dataset_service()

    return PerformanceAnalysisService(
        market_dataset_service=market_dataset_service,
    )


def build_correlation_analysis_service() -> CorrelationAnalysisService:
    return CorrelationAnalysisService(
        market_dataset_service=build_market_dataset_service(),
    )


def build_drawdown_analysis_service() -> DrawdownAnalysisService:
    return DrawdownAnalysisService(
        market_dataset_service=build_market_dataset_service(),
    )


def build_ranking_analysis_service() -> RankingAnalysisService:
    return RankingAnalysisService(
        market_dataset_service=build_market_dataset_service(),
    )
