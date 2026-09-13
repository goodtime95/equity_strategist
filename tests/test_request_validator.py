from datetime import date

import pytest

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


def test_missing_assets_and_universe_needs_clarification() -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(AnalysisMetric.PERFORMANCE,),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 1, 1),
        unresolved=("The assets to compare are not specified.",),
    )

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.NEEDS_CLARIFICATION

    assert any("asset or universe" in issue for issue in result.issues)


@pytest.mark.parametrize(
    ("assets", "expected_issue"),
    [
        ((), "exactly one asset"),
        (("LVMH", "Hermès"), "exactly one asset"),
        (("LVMH", "Hermès", "ASML"), "exactly one asset"),
    ],
)
def test_price_request_requires_exactly_one_asset(
    assets: tuple[str, ...],
    expected_issue: str,
) -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.GET,
        metrics=(AnalysisMetric.PRICE,),
        assets=assets,
        target_date=date(2025, 1, 1),
    )

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.NEEDS_CLARIFICATION
    assert any(expected_issue in issue for issue in result.issues)


def test_price_request_requires_target_date() -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.GET,
        metrics=(AnalysisMetric.PRICE,),
        assets=("LVMH",),
    )

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.NEEDS_CLARIFICATION
    assert "target date is required for price queries" in result.issues


def test_explicit_asset_count_is_checked_when_universe_is_also_present() -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.RANK,
        metrics=(AnalysisMetric.PERFORMANCE,),
        assets=("LVMH",),
        universe="CAC 40",
        start_date=date(2024, 1, 1),
        end_date=date(2025, 1, 1),
    )

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.NEEDS_CLARIFICATION
    assert any("at least two assets" in issue for issue in result.issues)


@pytest.mark.parametrize(
    ("objective", "metric"),
    [
        (AnalysisObjective.COMPARE, AnalysisMetric.PERFORMANCE),
        (AnalysisObjective.COMPARE, AnalysisMetric.VOLATILITY),
        (AnalysisObjective.COMPARE, AnalysisMetric.DRAWDOWN),
        (AnalysisObjective.ANALYZE, AnalysisMetric.CORRELATION),
        (AnalysisObjective.RANK, AnalysisMetric.PERFORMANCE),
        (AnalysisObjective.RANK, AnalysisMetric.VOLATILITY),
    ],
)
def test_multi_asset_capabilities_reject_one_explicit_asset(
    objective: AnalysisObjective,
    metric: AnalysisMetric,
) -> None:
    request = AnalysisRequest(
        objective=objective,
        metrics=(metric,),
        assets=("LVMH",),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 1, 1),
    )

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.NEEDS_CLARIFICATION
    assert any("at least two assets" in issue for issue in result.issues)


@pytest.mark.parametrize(
    ("assets", "universe", "expected_issue"),
    [
        ((" ",), None, "asset queries cannot be blank"),
        ((), " ", "universe cannot be blank"),
        (("LVMH", " lvmh "), None, "duplicate asset queries"),
    ],
)
def test_blank_or_duplicate_identifiers_need_clarification(
    assets: tuple[str, ...],
    universe: str | None,
    expected_issue: str,
) -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.RANK,
        metrics=(AnalysisMetric.PERFORMANCE,),
        assets=assets,
        universe=universe,
        start_date=date(2024, 1, 1),
        end_date=date(2025, 1, 1),
    )

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.NEEDS_CLARIFICATION
    assert any(expected_issue in issue for issue in result.issues)


def test_multi_metric_universe_request_reports_unsupported_capability() -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.RANK,
        metrics=(AnalysisMetric.PERFORMANCE, AnalysisMetric.VOLATILITY),
        universe="CAC 40",
        start_date=date(2024, 1, 1),
        end_date=date(2025, 1, 1),
    )

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.UNSUPPORTED
    assert "capability does not currently support universes: rank_volatility" in (
        result.issues
    )


@pytest.mark.parametrize(
    ("objective", "metric", "assets", "universe", "target_date"),
    [
        (
            AnalysisObjective.GET,
            AnalysisMetric.PRICE,
            ("LVMH",),
            None,
            date(2025, 1, 1),
        ),
        (
            AnalysisObjective.COMPARE,
            AnalysisMetric.PERFORMANCE,
            ("LVMH", "Hermès"),
            None,
            None,
        ),
        (
            AnalysisObjective.COMPARE,
            AnalysisMetric.VOLATILITY,
            ("LVMH", "Hermès"),
            None,
            None,
        ),
        (
            AnalysisObjective.COMPARE,
            AnalysisMetric.DRAWDOWN,
            ("LVMH", "Hermès"),
            None,
            None,
        ),
        (
            AnalysisObjective.ANALYZE,
            AnalysisMetric.CORRELATION,
            ("LVMH", "Hermès"),
            None,
            None,
        ),
        (
            AnalysisObjective.RANK,
            AnalysisMetric.PERFORMANCE,
            ("LVMH", "Hermès"),
            None,
            None,
        ),
        (
            AnalysisObjective.RANK,
            AnalysisMetric.VOLATILITY,
            ("LVMH", "Hermès"),
            None,
            None,
        ),
        (AnalysisObjective.RANK, AnalysisMetric.PERFORMANCE, (), "CAC 40", None),
    ],
)
def test_supported_capability_has_a_structurally_ready_request(
    objective: AnalysisObjective,
    metric: AnalysisMetric,
    assets: tuple[str, ...],
    universe: str | None,
    target_date: date | None,
) -> None:
    period_dates = (
        {}
        if metric == AnalysisMetric.PRICE
        else {
            "start_date": date(2024, 1, 1),
            "end_date": date(2025, 1, 1),
        }
    )
    request = AnalysisRequest(
        objective=objective,
        metrics=(metric,),
        assets=assets,
        universe=universe,
        target_date=target_date,
        **period_dates,
    )

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.READY
    assert result.issues == ()
