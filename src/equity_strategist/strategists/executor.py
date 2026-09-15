from equity_strategist.domain.analysis_execution import (
    AnalysisExecutionResult,
    StepExecutionResult,
)
from equity_strategist.domain.analysis_plan import (
    AnalysisPlan,
    Capability,
)
from equity_strategist.domain.analysis_request import RankingDirection
from equity_strategist.domain.market_dataset import (
    AlignedMarketDataset,
    MarketDatasetBundle,
)
from equity_strategist.services.correlation_analysis import (
    CorrelationAnalysisService,
)
from equity_strategist.services.drawdown_analysis import (
    DrawdownAnalysisService,
)
from equity_strategist.services.market_dataset import MarketDatasetService
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
        market_dataset_service: MarketDatasetService | None = None,
    ) -> None:
        self.volatility_analysis_service = volatility_analysis_service
        self.performance_analysis_service = performance_analysis_service
        self.correlation_analysis_service = correlation_analysis_service
        self.drawdown_analysis_service = drawdown_analysis_service
        self.ranking_analysis_service = ranking_analysis_service
        self.market_query_service = market_query_service
        self.universe_constituent_service = universe_constituent_service
        self.universe_asset_resolver = universe_asset_resolver
        self.market_dataset_service = market_dataset_service

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
        shared_bundle, shared_aligned = self._build_shared_dataset(plan)

        for step in plan.steps:
            result = self._execute_step(
                capability=step.capability,
                plan=plan,
                shared_bundle=shared_bundle,
                shared_aligned=shared_aligned,
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
        shared_bundle: MarketDatasetBundle | None = None,
        shared_aligned: AlignedMarketDataset | None = None,
    ) -> object:
        request = plan.request

        if capability == Capability.COMPARE_VOLATILITY:
            if request.start_date is None:
                raise ValueError("COMPARE_VOLATILITY requires start_date")

            if request.end_date is None:
                raise ValueError("COMPARE_VOLATILITY requires end_date")

            if shared_aligned is not None:
                return self.volatility_analysis_service.compare_aligned(shared_aligned)
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
            if request.start_date is None and not request.horizons:
                raise ValueError("COMPARE_PERFORMANCE requires start_date")

            if request.end_date is None:
                raise ValueError("COMPARE_PERFORMANCE requires end_date")

            if shared_bundle is not None:
                periods = self.performance_analysis_service.resolve_requested_periods(
                    request.start_date,
                    request.end_date,
                    request.horizons,
                )
                return self.performance_analysis_service.analyze_bundle(
                    bundle=shared_bundle,
                    periods=periods,
                    performance_measure=request.performance_measure,
                )
            if (
                request.performance_measure.value == "total"
                and not request.horizons
                and request.benchmark is None
            ):
                return self.performance_analysis_service.compare(
                    asset_queries=list(request.assets),
                    start_date=request.start_date,
                    end_date=request.end_date,
                )
            return self.performance_analysis_service.compare(
                asset_queries=list(request.assets),
                start_date=request.start_date,
                end_date=request.end_date,
                performance_measure=request.performance_measure,
                horizons=request.horizons,
                benchmark=request.benchmark,
            )

        if capability == Capability.ANALYZE_CORRELATION:
            if request.start_date is None:
                raise ValueError("ANALYZE_CORRELATION requires start_date")

            if request.end_date is None:
                raise ValueError("ANALYZE_CORRELATION requires end_date")

            if shared_aligned is not None:
                return self.correlation_analysis_service.analyze_aligned(shared_aligned)
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

            if shared_aligned is not None:
                return self.drawdown_analysis_service.compare_aligned(shared_aligned)
            return self.drawdown_analysis_service.compare(
                asset_queries=list(request.assets),
                start_date=request.start_date,
                end_date=request.end_date,
            )

        if capability == Capability.RANK_PERFORMANCE:
            if request.start_date is None and not request.horizons:
                raise ValueError("RANK_PERFORMANCE requires start_date")

            if request.end_date is None:
                raise ValueError("RANK_PERFORMANCE requires end_date")

            if request.assets:
                if shared_bundle is not None:
                    periods = (
                        self.performance_analysis_service.resolve_requested_periods(
                            request.start_date,
                            request.end_date,
                            request.horizons,
                        )
                    )
                    return self.performance_analysis_service.analyze_bundle(
                        bundle=shared_bundle,
                        periods=periods,
                        performance_measure=request.performance_measure,
                        ranking_direction=(
                            request.ranking_direction or RankingDirection.HIGHEST
                        ),
                        top_n=request.top_n,
                    )
                if (
                    request.performance_measure.value == "total"
                    and not request.horizons
                    and request.benchmark is None
                ):
                    return self.ranking_analysis_service.rank_performance(
                        asset_queries=list(request.assets),
                        start_date=request.start_date,
                        end_date=request.end_date,
                        ranking_direction=(
                            request.ranking_direction or RankingDirection.HIGHEST
                        ),
                        top_n=request.top_n,
                    )
                return self.ranking_analysis_service.rank_performance(
                    asset_queries=list(request.assets),
                    start_date=request.start_date,
                    end_date=request.end_date,
                    ranking_direction=(
                        request.ranking_direction or RankingDirection.HIGHEST
                    ),
                    top_n=request.top_n,
                    performance_measure=request.performance_measure,
                    horizons=request.horizons,
                    benchmark=request.benchmark,
                )

            if request.universe is not None:
                constituents = self.universe_constituent_service.get_constituents(
                    request.universe
                )

                assets = self.universe_asset_resolver.resolve_many(constituents)

                if (
                    request.performance_measure.value == "total"
                    and not request.horizons
                    and request.benchmark is None
                ):
                    return self.ranking_analysis_service.rank_performance_for_assets(
                        assets=assets,
                        start_date=request.start_date,
                        end_date=request.end_date,
                        universe=request.universe,
                        ranking_direction=(
                            request.ranking_direction or RankingDirection.HIGHEST
                        ),
                        top_n=request.top_n,
                    )
                return self.ranking_analysis_service.rank_performance_for_assets(
                    assets=assets,
                    start_date=request.start_date,
                    end_date=request.end_date,
                    universe=request.universe,
                    ranking_direction=(
                        request.ranking_direction or RankingDirection.HIGHEST
                    ),
                    top_n=request.top_n,
                    performance_measure=request.performance_measure,
                    horizons=request.horizons,
                    benchmark=request.benchmark,
                )

            raise ValueError("RANK_PERFORMANCE requires assets or universe")

        if capability == Capability.RANK_VOLATILITY:
            if request.start_date is None:
                raise ValueError("RANK_VOLATILITY requires start_date")

            if request.end_date is None:
                raise ValueError("RANK_VOLATILITY requires end_date")

            if shared_aligned is not None:
                return self.ranking_analysis_service.rank_volatility_aligned(
                    aligned=shared_aligned,
                    ranking_direction=(
                        request.ranking_direction or RankingDirection.HIGHEST
                    ),
                    top_n=request.top_n,
                )
            return self.ranking_analysis_service.rank_volatility(
                asset_queries=list(request.assets),
                start_date=request.start_date,
                end_date=request.end_date,
                ranking_direction=(
                    request.ranking_direction or RankingDirection.HIGHEST
                ),
                top_n=request.top_n,
            )

        raise ValueError(f"unsupported capability: {capability}")

    def _build_shared_dataset(
        self,
        plan: AnalysisPlan,
    ) -> tuple[MarketDatasetBundle | None, AlignedMarketDataset | None]:
        """Build one runtime dataset for compatible explicit-period steps."""
        request = plan.request
        compatible = {
            Capability.COMPARE_PERFORMANCE,
            Capability.COMPARE_VOLATILITY,
            Capability.COMPARE_DRAWDOWN,
            Capability.ANALYZE_CORRELATION,
            Capability.RANK_PERFORMANCE,
            Capability.RANK_VOLATILITY,
        }
        if (
            self.market_dataset_service is None
            or len(plan.steps) < 2
            or not request.assets
            or request.start_date is None
            or request.end_date is None
            or request.horizons
            or any(step.capability not in compatible for step in plan.steps)
        ):
            return None, None

        assert self.market_dataset_service is not None
        bundle = self.market_dataset_service.build_price_dataset_bundle(
            asset_queries=list(request.assets),
            start_date=self.market_dataset_service.history_fetch_start(
                request.start_date
            ),
            end_date=request.end_date,
            benchmark_query=request.benchmark,
        )
        aligned = self.market_dataset_service.align_price_dataset(
            bundle=bundle,
            requested_start_date=request.start_date,
            requested_end_date=request.end_date,
        )
        return bundle, aligned
