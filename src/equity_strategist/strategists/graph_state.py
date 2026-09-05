from datetime import date
from typing import Annotated, TypedDict

from langgraph.channels import UntrackedValue

from equity_strategist.domain.analysis_execution import (
    AnalysisExecutionResult,
)
from equity_strategist.domain.analysis_plan import AnalysisPlan
from equity_strategist.domain.analysis_request import (
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
)
from equity_strategist.domain.request_validation import (
    RequestStatus,
    RequestValidationResult,
)


class AnalysisRequestState(TypedDict):
    """Serializable representation of an AnalysisRequest."""

    objective: str
    metrics: list[str]

    assets: list[str]
    universe: str | None

    start_date: str | None
    end_date: str | None
    target_date: str | None
    market_period: str | None

    benchmark: str | None

    constraints: list[str]
    user_context: str | None
    unresolved: list[str]


class RequestValidationState(TypedDict):
    """Serializable representation of request validation."""

    status: str
    issues: list[str]


class EquityGraphState(TypedDict, total=False):
    """Internal LangGraph state.

    Only simple serializable values are persisted.
    Plan and execution objects are transient and never checkpointed.
    """

    question: str

    request: AnalysisRequestState
    validation: RequestValidationState

    plan: Annotated[AnalysisPlan, UntrackedValue]
    execution: Annotated[
        AnalysisExecutionResult,
        UntrackedValue,
    ]

    answer: str


class EquityGraphResult(TypedDict, total=False):
    """Public result returned by EquityStrategistGraph.invoke."""

    question: str
    request: AnalysisRequest
    validation: RequestValidationResult
    plan: AnalysisPlan
    execution: AnalysisExecutionResult
    answer: str


def analysis_request_to_state(
    request: AnalysisRequest,
) -> AnalysisRequestState:
    return {
        "objective": request.objective.value,
        "metrics": [metric.value for metric in request.metrics],
        "assets": list(request.assets),
        "universe": request.universe,
        "start_date": _date_to_string(request.start_date),
        "end_date": _date_to_string(request.end_date),
        "target_date": _date_to_string(request.target_date),
        "market_period": request.market_period,
        "benchmark": request.benchmark,
        "constraints": list(request.constraints),
        "user_context": request.user_context,
        "unresolved": list(request.unresolved),
    }


def analysis_request_from_state(
    data: AnalysisRequestState,
) -> AnalysisRequest:
    return AnalysisRequest(
        objective=AnalysisObjective(data["objective"]),
        metrics=tuple(AnalysisMetric(metric) for metric in data["metrics"]),
        assets=tuple(data["assets"]),
        universe=data["universe"],
        start_date=_date_from_string(data["start_date"]),
        end_date=_date_from_string(data["end_date"]),
        target_date=_date_from_string(data["target_date"]),
        market_period=data["market_period"],
        benchmark=data["benchmark"],
        constraints=tuple(data["constraints"]),
        user_context=data["user_context"],
        unresolved=tuple(data["unresolved"]),
    )


def validation_to_state(
    validation: RequestValidationResult,
) -> RequestValidationState:
    return {
        "status": validation.status.value,
        "issues": list(validation.issues),
    }


def validation_from_state(
    data: RequestValidationState,
) -> RequestValidationResult:
    return RequestValidationResult(
        status=RequestStatus(data["status"]),
        issues=tuple(data["issues"]),
    )


def _date_to_string(
    value: date | None,
) -> str | None:
    if value is None:
        return None

    return value.isoformat()


def _date_from_string(
    value: str | None,
) -> date | None:
    if value is None:
        return None

    return date.fromisoformat(value)
