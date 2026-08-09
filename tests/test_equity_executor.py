from datetime import date
from decimal import Decimal

from equity_strategist.domain.analysis_execution import (
    AnalysisExecutionResult,
)
from equity_strategist.domain.analysis_plan import (
    AnalysisPlan,
    Capability,
    PlanStep,
)
from equity_strategist.domain.analysis_request import (
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
)
from equity_strategist.domain.analysis_results import (
    CorrelationAnalysisResult,
    CorrelationItem,
    DrawdownComparisonResult,
    DrawdownItem,
    PerformanceComparisonResult,
    PerformanceItem,
    RankingItem,
    RankingResult,
    VolatilityComparisonResult,
    VolatilityItem,
)
from equity_strategist.domain.asset import Asset
from equity_strategist.domain.results import PriceOnDateResult
from equity_strategist.strategists.executor import EquityExecutor


class FakeVolatilityAnalysisService:
    def compare(
        self,
        asset_queries,
        start_date,
        end_date,
        annualization_factor=252,
        return_method=None,
    ):
        return VolatilityComparisonResult(
            start_date=start_date,
            end_date=end_date,
            annualization_factor=annualization_factor,
            items=(
                VolatilityItem(
                    symbol="MC.PA",
                    name="LVMH",
                    volatility=0.30,
                ),
                VolatilityItem(
                    symbol="RMS.PA",
                    name="Hermès",
                    volatility=0.25,
                ),
            ),
        )


class FakeMarketQueryService:
    def get_price_on_date(
        self,
        asset_query,
        target_date,
        preferred_exchange=None,
        preferred_currency=None,
        use_adjusted_close=True,
    ):
        return PriceOnDateResult(
            asset=Asset(
                symbol="MC.PA",
                name="LVMH",
                currency="EUR",
            ),
            requested_date=target_date,
            effective_date=target_date,
            price=Decimal("500"),
            price_type="adjusted_close",
            used_previous_session=False,
        )


class FakePerformanceAnalysisService:
    def compare(
        self,
        asset_queries,
        start_date,
        end_date,
    ):
        return PerformanceComparisonResult(
            start_date=start_date,
            end_date=end_date,
            items=(
                PerformanceItem(
                    symbol="MC.PA",
                    name="LVMH",
                    performance=0.20,
                ),
                PerformanceItem(
                    symbol="RMS.PA",
                    name="Hermès",
                    performance=0.15,
                ),
            ),
        )


class FakeCorrelationAnalysisService:
    def analyze(
        self,
        asset_queries,
        start_date,
        end_date,
    ):
        return CorrelationAnalysisResult(
            start_date=start_date,
            end_date=end_date,
            items=(
                CorrelationItem(
                    first_symbol="MC.PA",
                    first_name="LVMH",
                    second_symbol="RMS.PA",
                    second_name="Hermès",
                    correlation=0.72,
                ),
            ),
        )


class FakeDrawdownAnalysisService:
    def compare(
        self,
        asset_queries,
        start_date,
        end_date,
    ):
        return DrawdownComparisonResult(
            start_date=start_date,
            end_date=end_date,
            items=(
                DrawdownItem(
                    symbol="MC.PA",
                    name="LVMH",
                    maximum_drawdown=-0.35,
                    peak_date=date(2024, 3, 1),
                    trough_date=date(2024, 8, 1),
                    recovery_date=None,
                ),
                DrawdownItem(
                    symbol="RMS.PA",
                    name="Hermès",
                    maximum_drawdown=-0.20,
                    peak_date=date(2024, 2, 1),
                    trough_date=date(2024, 6, 1),
                    recovery_date=date(2025, 1, 15),
                ),
            ),
        )


class FakeRankingAnalysisService:
    def rank_performance(
        self,
        asset_queries,
        start_date,
        end_date,
    ):
        return RankingResult(
            metric="performance",
            start_date=start_date,
            end_date=end_date,
            items=(
                RankingItem(
                    rank=1,
                    symbol="ASML.AS",
                    name="ASML",
                    value=0.40,
                ),
                RankingItem(
                    rank=2,
                    symbol="MC.PA",
                    name="LVMH",
                    value=0.20,
                ),
                RankingItem(
                    rank=3,
                    symbol="RMS.PA",
                    name="Hermès",
                    value=0.10,
                ),
            ),
        )


def build_executor():
    return EquityExecutor(
        volatility_analysis_service=FakeVolatilityAnalysisService(),
        performance_analysis_service=FakePerformanceAnalysisService(),
        correlation_analysis_service=FakeCorrelationAnalysisService(),
        drawdown_analysis_service=FakeDrawdownAnalysisService(),
        ranking_analysis_service=FakeRankingAnalysisService(),
        market_query_service=FakeMarketQueryService(),
    )


def test_execute_volatility_plan():
    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(AnalysisMetric.VOLATILITY,),
        assets=("LVMH", "Hermès"),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
    )

    plan = AnalysisPlan(
        request=request,
        steps=(
            PlanStep(
                capability=Capability.COMPARE_VOLATILITY,
            ),
        ),
    )

    result = build_executor().execute(plan)

    assert isinstance(
        result,
        AnalysisExecutionResult,
    )

    assert len(result.step_results) == 1

    assert result.step_results[0].capability == Capability.COMPARE_VOLATILITY


def test_execute_price_on_date_plan():
    request = AnalysisRequest(
        objective=AnalysisObjective.GET,
        metrics=(AnalysisMetric.PRICE,),
        assets=("LVMH",),
        target_date=date(2020, 3, 13),
    )

    plan = AnalysisPlan(
        request=request,
        steps=(
            PlanStep(
                capability=Capability.PRICE_ON_DATE,
            ),
        ),
    )

    result = build_executor().execute(plan)

    price = result.step_results[0].result

    assert isinstance(
        price,
        PriceOnDateResult,
    )

    assert price.asset.symbol == "MC.PA"

    assert price.price == Decimal("500")


def test_execute_performance_plan():
    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(AnalysisMetric.PERFORMANCE,),
        assets=("LVMH", "Hermès"),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
    )

    plan = AnalysisPlan(
        request=request,
        steps=(
            PlanStep(
                capability=Capability.COMPARE_PERFORMANCE,
            ),
        ),
    )

    result = build_executor().execute(plan)

    performance_result = result.step_results[0].result

    assert isinstance(
        performance_result,
        PerformanceComparisonResult,
    )
    assert len(performance_result.items) == 2
    assert performance_result.items[0].symbol == "MC.PA"


def test_execute_correlation_plan():
    request = AnalysisRequest(
        objective=AnalysisObjective.ANALYZE,
        metrics=(AnalysisMetric.CORRELATION,),
        assets=("LVMH", "Hermès"),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
    )

    plan = AnalysisPlan(
        request=request,
        steps=(
            PlanStep(
                capability=Capability.ANALYZE_CORRELATION,
            ),
        ),
    )

    result = build_executor().execute(plan)

    correlation_result = result.step_results[0].result

    assert isinstance(
        correlation_result,
        CorrelationAnalysisResult,
    )
    assert len(correlation_result.items) == 1
    assert correlation_result.items[0].correlation == 0.72


def test_execute_drawdown_plan():
    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(AnalysisMetric.DRAWDOWN,),
        assets=("LVMH", "Hermès"),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
    )

    plan = AnalysisPlan(
        request=request,
        steps=(
            PlanStep(
                capability=Capability.COMPARE_DRAWDOWN,
            ),
        ),
    )

    result = build_executor().execute(plan)

    drawdown_result = result.step_results[0].result

    assert isinstance(
        drawdown_result,
        DrawdownComparisonResult,
    )
    assert len(drawdown_result.items) == 2
    assert drawdown_result.items[0].maximum_drawdown == -0.35


def test_execute_performance_ranking_plan():
    request = AnalysisRequest(
        objective=AnalysisObjective.RANK,
        metrics=(AnalysisMetric.PERFORMANCE,),
        assets=("LVMH", "Hermès", "ASML"),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
    )

    plan = AnalysisPlan(
        request=request,
        steps=(
            PlanStep(
                capability=Capability.RANK_PERFORMANCE,
            ),
        ),
    )

    result = build_executor().execute(plan)

    ranking_result = result.step_results[0].result

    assert isinstance(
        ranking_result,
        RankingResult,
    )
    assert ranking_result.items[0].rank == 1
    assert ranking_result.items[0].symbol == "ASML.AS"
