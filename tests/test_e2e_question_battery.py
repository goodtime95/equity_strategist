"""Offline regression tests for the assertions in the existing live battery."""

import runpy
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from equity_strategist.domain.analysis_execution import (
    AnalysisExecutionResult,
    StepExecutionResult,
)
from equity_strategist.domain.analysis_request import (
    AnalysisRequest,
    PerformanceMeasure,
)
from equity_strategist.domain.analysis_results import (
    PerformanceAnalysisResult,
    PerformancePeriodResult,
)
from equity_strategist.strategists.planner import EquityPlanner
from equity_strategist.strategists.validator import AnalysisRequestValidator

BATTERY = runpy.run_path(
    str(Path(__file__).parents[1] / "scripts" / "e2e_question_battery.py")
)


def test_live_horizon_cases_have_anchor_expectations() -> None:
    assert len(BATTERY["CASES"]) == 26
    for case in BATTERY["CASES"]:
        if case.expected.horizons:
            assert case.expected.end_date is not None


@pytest.mark.parametrize(
    "mutation",
    [
        None,
        "request_anchor",
        "result_anchor",
        "effective_start",
        "effective_end",
        "horizons",
        "measure",
    ],
)
def test_battery_detects_historical_horizon_regressions(mutation: str | None) -> None:
    expected = next(
        case.expected for case in BATTERY["CASES"] if case.name == "ytd_performance"
    )
    request = AnalysisRequest(
        objective=expected.objective,
        metrics=expected.metrics,
        assets=expected.assets,
        horizons=expected.horizons,
        end_date=expected.end_date,
    )
    period = PerformancePeriodResult(
        horizon=expected.horizons[0],
        requested_start_date=date(2024, 1, 1),
        requested_end_date=date(2024, 12, 31),
        effective_start_date=date(2023, 12, 29),
        effective_end_date=date(2024, 12, 31),
        items=(),
    )
    if mutation == "request_anchor":
        request = replace(request, end_date=date(2026, 9, 15))
    elif mutation == "result_anchor":
        period = replace(period, requested_end_date=date(2026, 9, 15))
    elif mutation == "effective_start":
        period = replace(period, effective_start_date=date(2024, 1, 2))
    elif mutation == "effective_end":
        period = replace(period, effective_end_date=date(2024, 12, 30))
    elif mutation == "horizons":
        period = replace(period, horizon=None)
    result = PerformanceAnalysisResult(
        measure=PerformanceMeasure.ANNUALIZED
        if mutation == "measure"
        else PerformanceMeasure.TOTAL,
        periods=(period,),
    )
    plan = EquityPlanner().plan(request)
    execution = AnalysisExecutionResult(
        plan,
        (StepExecutionResult(plan.steps[0].capability, result),),
    )
    failures = BATTERY["_check_state"](
        dict(
            request=request,
            validation=AnalysisRequestValidator().validate(request),
            plan=plan,
            execution=execution,
            answer="Deterministic test answer",
        ),
        expected,
        False,
        [],
    )
    assert bool(failures) == (mutation is not None)
