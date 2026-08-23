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
from equity_strategist.services.market_queries import (
    MarketQueryService,
)
from equity_strategist.services.market_series import (
    MarketSeriesService,
)
from equity_strategist.services.performance_analysis import (
    PerformanceAnalysisService,
)
from equity_strategist.services.ranking_analysis import (
    RankingAnalysisService,
)
from equity_strategist.services.universe_constituents import (
    UniverseConstituentService,
)
from equity_strategist.services.volatility_analysis import (
    VolatilityAnalysisService,
)
from equity_strategist.strategists.equity_strategist import (
    EquityStrategist,
)
from equity_strategist.strategists.executor import EquityExecutor
from equity_strategist.strategists.planner import EquityPlanner
from equity_strategist.strategists.validator import (
    AnalysisRequestValidator,
)
from equity_strategist.tools.assets import AssetResolver
from equity_strategist.tools.prices import PriceTool
from equity_strategist.tools.universe_assets import (
    UniverseAssetResolver,
)
from equity_strategist.understanding.base import (
    UnderstandingProvider,
)
from equity_strategist.understanding.llm import (
    LLMUnderstanding,
)
from equity_strategist.understanding.rule_based import (
    RuleBasedUnderstanding,
)
from equity_strategist.universe_providers.euronext import (
    EuronextUniverseProvider,
)
from equity_strategist.universe_registry import (
    build_default_universe_registry,
)
from equity_strategist.universe_registry.registry import (
    UniverseRegistry,
)


def _build_equity_pipeline(
    understanding: UnderstandingProvider,
    universe_registry: UniverseRegistry,
) -> EquityStrategist:
    """Build the shared Equity Strategist dependency graph."""

    provider = YahooFinanceProvider()

    asset_registry = build_default_asset_registry()

    asset_resolver = AssetResolver(
        registry=asset_registry,
        fallback_provider=provider,
    )

    market_series_service = MarketSeriesService(
        provider=provider,
        asset_resolver=asset_resolver,
    )

    market_dataset_service = MarketDatasetService(
        market_series_service=market_series_service,
    )

    market_query_service = MarketQueryService(
        asset_resolver=asset_resolver,
        price_tool=PriceTool(provider),
    )

    performance_analysis_service = PerformanceAnalysisService(
        market_dataset_service=market_dataset_service,
    )

    volatility_analysis_service = VolatilityAnalysisService(
        market_dataset_service=market_dataset_service,
    )

    correlation_analysis_service = CorrelationAnalysisService(
        market_dataset_service=market_dataset_service,
    )

    drawdown_analysis_service = DrawdownAnalysisService(
        market_dataset_service=market_dataset_service,
    )

    ranking_analysis_service = RankingAnalysisService(
        market_dataset_service=market_dataset_service,
    )

    universe_constituent_service = UniverseConstituentService(
        universe_registry=universe_registry,
        universe_providers={
            "euronext": EuronextUniverseProvider(),
        },
    )

    universe_asset_resolver = UniverseAssetResolver(
        asset_resolver=asset_resolver,
    )

    planner = EquityPlanner()

    executor = EquityExecutor(
        volatility_analysis_service=(volatility_analysis_service),
        performance_analysis_service=(performance_analysis_service),
        correlation_analysis_service=(correlation_analysis_service),
        drawdown_analysis_service=(drawdown_analysis_service),
        ranking_analysis_service=(ranking_analysis_service),
        market_query_service=market_query_service,
        universe_constituent_service=(universe_constituent_service),
        universe_asset_resolver=(universe_asset_resolver),
    )

    return EquityStrategist(
        understanding=understanding,
        planner=planner,
        executor=executor,
        validator=AnalysisRequestValidator(),
    )


def build_equity_strategist() -> EquityStrategist:
    """Build the deterministic Equity Strategist pipeline."""

    universe_registry = build_default_universe_registry()

    return _build_equity_pipeline(
        understanding=RuleBasedUnderstanding(
            universe_registry=universe_registry,
        ),
        universe_registry=universe_registry,
    )


def build_llm_equity_strategist() -> EquityStrategist:
    """Build the LLM-powered Equity Strategist pipeline."""

    universe_registry = build_default_universe_registry()

    return _build_equity_pipeline(
        understanding=LLMUnderstanding(),
        universe_registry=universe_registry,
    )
