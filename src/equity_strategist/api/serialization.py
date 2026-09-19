from equity_strategist.api.schemas import (
    AnalysisRequestSnapshot,
    ChatResponse,
    ValidationSnapshot,
)
from equity_strategist.domain.request_validation import RequestStatus
from equity_strategist.interpretation.evidence import serialize_execution_evidence
from equity_strategist.strategists.graph_state import EquityGraphResult


def serialize_chat_result(
    result: EquityGraphResult,
    request_id: str,
    thread_id: str,
    include_evidence: bool,
) -> ChatResponse:
    """Map internal graph output to the stable v1 HTTP contract."""
    request = result["request"]
    validation = result["validation"]
    status = (
        "success"
        if validation.status == RequestStatus.READY
        else validation.status.value
    )
    evidence = None
    if include_evidence and validation.status == RequestStatus.READY:
        evidence = serialize_execution_evidence(result["execution"])

    return ChatResponse(
        request_id=request_id,
        thread_id=thread_id,
        status=status,
        answer=result["answer"],
        request=AnalysisRequestSnapshot(
            objective=request.objective.value,
            metrics=[metric.value for metric in request.metrics],
            assets=list(request.assets),
            universe=request.universe,
            start_date=_date(request.start_date),
            end_date=_date(request.end_date),
            target_date=_date(request.target_date),
            market_period=request.market_period,
            benchmark=request.benchmark,
            constraints=list(request.constraints),
            ranking_direction=(
                request.ranking_direction.value
                if request.ranking_direction is not None
                else None
            ),
            top_n=request.top_n,
            performance_measure=request.performance_measure.value,
            horizons=[horizon.value for horizon in request.horizons],
            user_context=request.user_context,
            unresolved=list(request.unresolved),
        ),
        validation=ValidationSnapshot(
            status=validation.status.value,
            issues=list(validation.issues),
        ),
        evidence=evidence,
    )


def _date(value) -> str | None:
    return value.isoformat() if value is not None else None
