from datetime import date

from equity_strategist.domain.analysis_plan import Capability
from equity_strategist.domain.analysis_request import (
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
)
from equity_strategist.strategists.planner import EquityPlanner


def test_plan_volatility_comparison() -> None:
    planner = EquityPlanner()

    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(AnalysisMetric.VOLATILITY,),
        assets=("LVMH", "Hermès"),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
    )

    plan = planner.plan(request)

    assert len(plan.steps) == 1
    assert plan.steps[0].capability == Capability.COMPARE_VOLATILITY


def test_plan_price_on_date() -> None:
    planner = EquityPlanner()

    request = AnalysisRequest(
        objective=AnalysisObjective.GET,
        metrics=(AnalysisMetric.PRICE,),
        assets=("LVMH",),
        target_date=date(2020, 3, 15),
    )

    plan = planner.plan(request)

    assert len(plan.steps) == 1
    assert plan.steps[0].capability == Capability.PRICE_ON_DATE


def test_plan_performance_comparison() -> None:
    planner = EquityPlanner()

    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(AnalysisMetric.PERFORMANCE,),
        assets=("LVMH", "Hermès"),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
    )

    plan = planner.plan(request)

    assert len(plan.steps) == 1
    assert plan.steps[0].capability == Capability.COMPARE_PERFORMANCE
