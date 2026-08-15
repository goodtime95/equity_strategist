from datetime import date

from equity_strategist.domain.analysis_request import (
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
)
from equity_strategist.domain.request_validation import (
    RequestStatus,
)
from equity_strategist.strategists.validator import (
    AnalysisRequestValidator,
)


def test_ready_request() -> None:
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
        end_date=date(2025, 1, 1),
    )

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.READY
    assert result.issues == ()


def test_missing_metric_needs_clarification() -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(),
        assets=(
            "Schneider Electric",
            "Safran",
        ),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 1, 1),
        unresolved=("La métrique à comparer n’est pas précisée.",),
    )

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.NEEDS_CLARIFICATION


def test_ambiguous_risk_needs_clarification() -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(AnalysisMetric.PERFORMANCE,),
        assets=(
            "LVMH",
            "Hermès",
        ),
        start_date=date(2021, 1, 1),
        end_date=date(2025, 1, 1),
        unresolved=("Risk could mean volatility or drawdown.",),
    )

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.NEEDS_CLARIFICATION


def test_rank_drawdown_is_understood_but_unsupported() -> None:
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

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.UNSUPPORTED

    assert any("rank + drawdown" in issue for issue in result.issues)


def test_missing_period_needs_clarification() -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(AnalysisMetric.PERFORMANCE,),
        assets=(
            "LVMH",
            "Hermès",
        ),
    )

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.NEEDS_CLARIFICATION

    assert "start date is required" in result.issues
    assert "end date is required" in result.issues


def test_universe_performance_ranking_is_ready() -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.RANK,
        metrics=(AnalysisMetric.PERFORMANCE,),
        universe="CAC 40",
        start_date=date(2025, 1, 1),
        end_date=date(2026, 1, 1),
    )

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.READY


def test_universe_volatility_ranking_is_unsupported() -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.RANK,
        metrics=(AnalysisMetric.VOLATILITY,),
        universe="CAC 40",
        start_date=date(2025, 1, 1),
        end_date=date(2026, 1, 1),
    )

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.UNSUPPORTED
