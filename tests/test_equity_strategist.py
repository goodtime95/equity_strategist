from datetime import date
from decimal import Decimal

from equity_strategist.domain.analysis_execution import (
    AnalysisExecutionResult,
    StepExecutionResult,
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
    PerformanceComparisonResult,
    PerformanceItem,
    VolatilityComparisonResult,
    VolatilityItem,
)
from equity_strategist.domain.asset import Asset
from equity_strategist.domain.results import PriceOnDateResult
from equity_strategist.strategists.equity_strategist import (
    EquityStrategist,
)
from equity_strategist.strategists.planner import EquityPlanner
from equity_strategist.strategists.validator import (
    AnalysisRequestValidator,
)


def test_interpret_volatility_result():
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

    result = VolatilityComparisonResult(
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
        annualization_factor=252,
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

    execution = AnalysisExecutionResult(
        plan=plan,
        step_results=(
            StepExecutionResult(
                capability=Capability.COMPARE_VOLATILITY,
                result=result,
            ),
        ),
    )

    strategist = EquityStrategist(
        understanding=None,
        planner=None,
        executor=None,
        validator=AnalysisRequestValidator(),
    )

    answer = strategist.interpret(execution)

    assert "LVMH" in answer
    assert "30.00%" in answer
    assert "Hermès" in answer
    assert "25.00%" in answer


def test_interpret_price_result():
    request = AnalysisRequest(
        objective=AnalysisObjective.GET,
        metrics=(AnalysisMetric.PRICE,),
        assets=("LVMH",),
        target_date=date(2020, 3, 15),
    )

    plan = AnalysisPlan(
        request=request,
        steps=(
            PlanStep(
                capability=Capability.PRICE_ON_DATE,
            ),
        ),
    )

    price_result = PriceOnDateResult(
        asset=Asset(
            symbol="MC.PA",
            name="LVMH",
            currency="EUR",
        ),
        requested_date=date(2020, 3, 15),
        effective_date=date(2020, 3, 13),
        price=Decimal("314.90"),
        price_type="close",
        used_previous_session=True,
    )

    execution = AnalysisExecutionResult(
        plan=plan,
        step_results=(
            StepExecutionResult(
                capability=Capability.PRICE_ON_DATE,
                result=price_result,
            ),
        ),
    )

    strategist = EquityStrategist(
        understanding=None,
        planner=None,
        executor=None,
        validator=AnalysisRequestValidator(),
    )

    answer = strategist.interpret(execution)

    assert "LVMH" in answer
    assert "314.90" in answer
    assert "2020-03-13" in answer
    assert "previous available trading session" in answer


def test_interpret_multiple_results() -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(
            AnalysisMetric.PERFORMANCE,
            AnalysisMetric.VOLATILITY,
        ),
        assets=(
            "LVMH",
            "Hermès",
        ),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
    )

    plan = AnalysisPlan(
        request=request,
        steps=(
            PlanStep(
                capability=Capability.COMPARE_PERFORMANCE,
            ),
            PlanStep(
                capability=Capability.COMPARE_VOLATILITY,
            ),
        ),
    )

    performance_result = PerformanceComparisonResult(
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
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

    volatility_result = VolatilityComparisonResult(
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
        annualization_factor=252,
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

    execution = AnalysisExecutionResult(
        plan=plan,
        step_results=(
            StepExecutionResult(
                capability=Capability.COMPARE_PERFORMANCE,
                result=performance_result,
            ),
            StepExecutionResult(
                capability=Capability.COMPARE_VOLATILITY,
                result=volatility_result,
            ),
        ),
    )

    strategist = EquityStrategist(
        understanding=None,
        planner=None,
        executor=None,
        validator=AnalysisRequestValidator(),
    )

    answer = strategist.interpret(execution)

    assert "Historical performance comparison" in answer
    assert "Historical volatility comparison" in answer

    assert "LVMH (MC.PA): 20.00%" in answer
    assert "LVMH (MC.PA): 30.00%" in answer


def test_answer_request_stops_when_clarification_is_needed() -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(),
        assets=(
            "Schneider Electric",
            "Safran",
        ),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 1, 1),
        unresolved=("The metric to compare is not specified.",),
    )

    strategist = EquityStrategist(
        understanding=None,
        planner=EquityPlanner(),
        executor=None,
        validator=AnalysisRequestValidator(),
    )

    answer = strategist.answer_request(request)

    assert "clarification" in answer.lower()
    assert "metric" in answer.lower()


def test_answer_request_stops_when_analysis_is_unsupported() -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.RANK,
        metrics=(AnalysisMetric.DRAWDOWN,),
        assets=(
            "LVMH",
            "Hermès",
            "ASML",
        ),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 1, 1),
    )

    strategist = EquityStrategist(
        understanding=None,
        planner=EquityPlanner(),
        executor=None,
        validator=AnalysisRequestValidator(),
    )

    answer = strategist.answer_request(request)

    assert "not supported yet" in answer.lower()
    assert "rank + drawdown" in answer.lower()
