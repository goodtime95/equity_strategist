from equity_strategist.domain.analysis_execution import (
    AnalysisExecutionResult,
    StepExecutionResult,
)
from equity_strategist.domain.analysis_plan import (
    AnalysisPlan,
    Capability,
)
from equity_strategist.services.correlation_analysis import (
    CorrelationAnalysisService,
)
from equity_strategist.services.drawdown_analysis import (
    DrawdownAnalysisService,
)
from equity_strategist.services.market_queries import (
    MarketQueryService,
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
from equity_strategist.tools.universe_assets import (
    UniverseAssetResolver,
)


class EquityExecutor:
    """Execute deterministic equity analysis plans."""

    def __init__(
        self,
        volatility_analysis_service: VolatilityAnalysisService,
        performance_analysis_service: PerformanceAnalysisService,
        correlation_analysis_service: CorrelationAnalysisService,
        drawdown_analysis_service: DrawdownAnalysisService,
        ranking_analysis_service: RankingAnalysisService,
        market_query_service: MarketQueryService,
        universe_constituent_service: UniverseConstituentService,
        universe_asset_resolver: UniverseAssetResolver,
    ) -> None:
        self.volatility_analysis_service = volatility_analysis_service
        self.performance_analysis_service = performance_analysis_service
        self.correlation_analysis_service = correlation_analysis_service
        self.drawdown_analysis_service = drawdown_analysis_service
        self.ranking_analysis_service = ranking_analysis_service
        self.market_query_service = market_query_service
        self.universe_constituent_service = universe_constituent_service
        self.universe_asset_resolver = universe_asset_resolver

    def _resolve_asset_queries(
        self,
        plan: AnalysisPlan,
    ) -> list[str]:
        request = plan.request

        if request.assets:
            return list(request.assets)

        if request.universe is not None:
            return list(
                self.universe_constituent_service.get_constituents(request.universe)
            )

        raise ValueError("analysis request requires assets or universe")

    def execute(
        self,
        plan: AnalysisPlan,
    ) -> AnalysisExecutionResult:
        """Execute all steps of an analysis plan."""
        step_results: list[StepExecutionResult] = []

        for step in plan.steps:
            result = self._execute_step(
                capability=step.capability,
                plan=plan,
            )

            step_results.append(
                StepExecutionResult(
                    capability=step.capability,
                    result=result,
                )
            )

        return AnalysisExecutionResult(
            plan=plan,
            step_results=tuple(step_results),
        )

    def _execute_step(
        self,
        capability: Capability,
        plan: AnalysisPlan,
    ) -> object:
        request = plan.request

        if capability == Capability.COMPARE_VOLATILITY:
            if request.start_date is None:
                raise ValueError("COMPARE_VOLATILITY requires start_date")

            if request.end_date is None:
                raise ValueError("COMPARE_VOLATILITY requires end_date")

            return self.volatility_analysis_service.compare(
                asset_queries=list(request.assets),
                start_date=request.start_date,
                end_date=request.end_date,
            )

        if capability == Capability.PRICE_ON_DATE:
            if len(request.assets) != 1:
                raise ValueError("PRICE_ON_DATE requires exactly one asset")

            if request.target_date is None:
                raise ValueError("PRICE_ON_DATE requires target_date")

            return self.market_query_service.get_price_on_date(
                asset_query=request.assets[0],
                target_date=request.target_date,
            )

        if capability == Capability.COMPARE_PERFORMANCE:
            if request.start_date is None:
                raise ValueError("COMPARE_PERFORMANCE requires start_date")

            if request.end_date is None:
                raise ValueError("COMPARE_PERFORMANCE requires end_date")

            return self.performance_analysis_service.compare(
                asset_queries=list(request.assets),
                start_date=request.start_date,
                end_date=request.end_date,
            )

        if capability == Capability.ANALYZE_CORRELATION:
            if request.start_date is None:
                raise ValueError("ANALYZE_CORRELATION requires start_date")

            if request.end_date is None:
                raise ValueError("ANALYZE_CORRELATION requires end_date")

            return self.correlation_analysis_service.analyze(
                asset_queries=list(request.assets),
                start_date=request.start_date,
                end_date=request.end_date,
            )

        if capability == Capability.COMPARE_DRAWDOWN:
            if request.start_date is None:
                raise ValueError("COMPARE_DRAWDOWN requires start_date")

            if request.end_date is None:
                raise ValueError("COMPARE_DRAWDOWN requires end_date")

            return self.drawdown_analysis_service.compare(
                asset_queries=list(request.assets),
                start_date=request.start_date,
                end_date=request.end_date,
            )

        if capability == Capability.RANK_PERFORMANCE:
            if request.start_date is None:
                raise ValueError("RANK_PERFORMANCE requires start_date")

            if request.end_date is None:
                raise ValueError("RANK_PERFORMANCE requires end_date")

            if request.assets:
                return self.ranking_analysis_service.rank_performance(
                    asset_queries=list(request.assets),
                    start_date=request.start_date,
                    end_date=request.end_date,
                )

            if request.universe is not None:
                constituents = self.universe_constituent_service.get_constituents(
                    request.universe
                )

                assets = self.universe_asset_resolver.resolve_many(constituents)

                return self.ranking_analysis_service.rank_performance_for_assets(
                    assets=assets,
                    start_date=request.start_date,
                    end_date=request.end_date,
                    universe=request.universe,
                )

            raise ValueError("RANK_PERFORMANCE requires assets or universe")

        if capability == Capability.RANK_VOLATILITY:
            if request.start_date is None:
                raise ValueError("RANK_VOLATILITY requires start_date")

            if request.end_date is None:
                raise ValueError("RANK_VOLATILITY requires end_date")

            return self.ranking_analysis_service.rank_volatility(
                asset_queries=list(request.assets),
                start_date=request.start_date,
                end_date=request.end_date,
            )

        raise ValueError(f"unsupported capability: {capability}")
