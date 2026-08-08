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
    VolatilityComparisonResult,
    VolatilityItem,
)
from equity_strategist.domain.asset import Asset
from equity_strategist.domain.results import PriceOnDateResult
from equity_strategist.strategists.equity_strategist import (
    EquityStrategist,
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
        planner=None,
        executor=None,
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
        planner=None,
        executor=None,
    )

    answer = strategist.interpret(execution)

    assert "LVMH" in answer
    assert "314.90" in answer
    assert "2020-03-13" in answer
    assert "previous available trading session" in answer
