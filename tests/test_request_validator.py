from datetime import date

import pytest

from equity_strategist.domain.analysis_request import (
    AmbiguityScope,
    AnalysisHorizon,
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
    PerformanceMeasure,
    RankingDirection,
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
    assert result.issue_codes == ("universe_capability_unsupported",)
    assert "rank_volatility" not in " ".join(result.issues)


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


@pytest.mark.parametrize(
    ("request_kwargs", "expected_issue"),
    [
        ({"constraints": ("EUR only",)}, "constraints"),
        ({"market_period": "1y"}, "market_period"),
    ],
)
def test_unsupported_modifiers_are_explicitly_rejected(
    request_kwargs: dict,
    expected_issue: str,
) -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(AnalysisMetric.PERFORMANCE,),
        assets=("LVMH", "Hermès"),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 1, 1),
        **request_kwargs,
    )

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.UNSUPPORTED
    assert any(expected_issue in issue for issue in result.issues)


def test_assets_and_universe_require_clarification() -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.RANK,
        metrics=(AnalysisMetric.PERFORMANCE,),
        assets=("LVMH", "Hermès"),
        universe="CAC 40",
        start_date=date(2024, 1, 1),
        end_date=date(2025, 1, 1),
    )

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.NEEDS_CLARIFICATION
    assert any("specify one asset source" in issue for issue in result.issues)


@pytest.mark.parametrize(
    "request_kwargs",
    [
        {"ranking_direction": RankingDirection.LOWEST},
        {"top_n": 1},
    ],
)
def test_ranking_controls_are_unsupported_for_non_ranking_requests(
    request_kwargs: dict,
) -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(AnalysisMetric.PERFORMANCE,),
        assets=("LVMH", "Hermès"),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 1, 1),
        **request_kwargs,
    )

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.UNSUPPORTED


def test_ranking_controls_are_supported_for_ranking_requests() -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.RANK,
        metrics=(AnalysisMetric.VOLATILITY,),
        assets=("LVMH", "Hermès", "ASML"),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 1, 1),
        ranking_direction=RankingDirection.LOWEST,
        top_n=2,
    )

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.READY


@pytest.mark.parametrize(
    ("request_case", "expected_issue"),
    [
        (
            AnalysisRequest(
                objective=AnalysisObjective.GET,
                metrics=(AnalysisMetric.PRICE,),
                assets=("LVMH",),
                target_date=date(2025, 1, 1),
                start_date=date(2024, 1, 1),
                end_date=date(2025, 1, 1),
            ),
            "period-based metrics",
        ),
        (
            AnalysisRequest(
                objective=AnalysisObjective.COMPARE,
                metrics=(AnalysisMetric.PERFORMANCE,),
                assets=("LVMH", "Hermès"),
                start_date=date(2024, 1, 1),
                end_date=date(2025, 1, 1),
                target_date=date(2025, 1, 1),
            ),
            "target_date",
        ),
    ],
)
def test_irrelevant_date_parameters_are_explicitly_rejected(
    request_case: AnalysisRequest,
    expected_issue: str,
) -> None:
    result = AnalysisRequestValidator().validate(request_case)

    assert result.status == RequestStatus.UNSUPPORTED
    assert any(expected_issue in issue for issue in result.issues)


@pytest.mark.parametrize(
    "measure",
    [PerformanceMeasure.TOTAL, PerformanceMeasure.ANNUALIZED],
)
def test_performance_horizon_request_is_ready(measure: PerformanceMeasure) -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(AnalysisMetric.PERFORMANCE,),
        assets=("LVMH", "Hermès"),
        end_date=date(2025, 1, 5),
        performance_measure=measure,
        horizons=(AnalysisHorizon.ONE_MONTH, AnalysisHorizon.YEAR_TO_DATE),
    )

    assert AnalysisRequestValidator().validate(request).status == RequestStatus.READY


@pytest.mark.parametrize(
    "measure",
    [PerformanceMeasure.RELATIVE, PerformanceMeasure.EXCESS_RETURN],
)
def test_relative_measure_requires_benchmark(measure: PerformanceMeasure) -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(AnalysisMetric.PERFORMANCE,),
        assets=("LVMH", "Hermès"),
        end_date=date(2025, 1, 5),
        performance_measure=measure,
        horizons=(AnalysisHorizon.ONE_YEAR,),
    )

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.NEEDS_CLARIFICATION
    assert "requires a benchmark" in result.issues[0]


def test_benchmark_total_performance_is_ready() -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(AnalysisMetric.PERFORMANCE,),
        assets=("LVMH", "Hermès"),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 1, 1),
        benchmark="S&P 500",
    )

    assert AnalysisRequestValidator().validate(request).status == RequestStatus.READY


def test_horizon_and_explicit_start_require_clarification() -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(AnalysisMetric.PERFORMANCE,),
        assets=("LVMH", "Hermès"),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 1, 1),
        horizons=(AnalysisHorizon.ONE_YEAR,),
    )

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.NEEDS_CLARIFICATION
    assert "must not include start_date" in result.issues[0]


def test_horizon_with_non_performance_metric_requires_clarification() -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(AnalysisMetric.PERFORMANCE, AnalysisMetric.VOLATILITY),
        assets=("LVMH", "Hermès"),
        end_date=date(2025, 1, 1),
        horizons=(AnalysisHorizon.ONE_YEAR,),
    )

    result = AnalysisRequestValidator().validate(request)

    assert result.status == RequestStatus.NEEDS_CLARIFICATION
    assert any("cannot currently be combined" in issue for issue in result.issues)


@pytest.mark.parametrize("universe", ["CAC 40", "Luxury Europe", "CAC40"])
def test_available_universe_is_ready(universe):
    request = AnalysisRequest(
        objective=AnalysisObjective.RANK,
        metrics=(AnalysisMetric.PERFORMANCE,),
        universe=universe,
        end_date=date(2026, 9, 24),
        horizons=(AnalysisHorizon.ONE_MONTH,),
    )
    assert AnalysisRequestValidator().validate(request).status == RequestStatus.READY


@pytest.mark.parametrize("universe", ["eurostoxx 50", "Unknown universe"])
def test_unavailable_universe_never_ready(universe):
    request = AnalysisRequest(
        objective=AnalysisObjective.RANK,
        metrics=(AnalysisMetric.PERFORMANCE,),
        universe=universe,
        end_date=date(2026, 9, 24),
        horizons=(AnalysisHorizon.ONE_MONTH,),
    )
    result = AnalysisRequestValidator().validate(request)
    assert result.status == RequestStatus.UNSUPPORTED
    assert result.issue_codes == (
        ("universe_unavailable", "index_asset_available")
        if universe == "eurostoxx 50"
        else ("universe_unavailable",)
    )


def test_injected_universe_catalog_and_ambiguous_alias():
    from dataclasses import replace

    from equity_strategist.domain.universe import Universe, UniverseType
    from equity_strategist.universe_registry.registry import UniverseRegistry

    universe = Universe(
        name="Custom",
        universe_type=UniverseType.STATIC,
        asset_queries=("LVMH", "Hermès"),
        aliases=("shared",),
    )
    request = AnalysisRequest(
        objective=AnalysisObjective.RANK,
        metrics=(AnalysisMetric.PERFORMANCE,),
        universe="Custom",
        end_date=date(2026, 9, 24),
        horizons=(AnalysisHorizon.ONE_MONTH,),
    )
    validator = AnalysisRequestValidator(UniverseRegistry([universe]))
    assert validator.validate(request).status == RequestStatus.READY
    assert AnalysisRequestValidator(UniverseRegistry([])).validate(request).status == (
        RequestStatus.UNSUPPORTED
    )
    validator = AnalysisRequestValidator(
        UniverseRegistry([universe, replace(universe, name="Other")])
    )
    result = validator.validate(replace(request, universe="shared"))
    assert result.status == RequestStatus.NEEDS_CLARIFICATION
    assert result.issue_codes == ("ambiguous_universe",)


@pytest.mark.parametrize(
    "constraints,expected",
    [
        ((), RequestStatus.NEEDS_CLARIFICATION),
        (("currency conversion",), RequestStatus.UNSUPPORTED),
    ],
)
def test_sector_reference_only_defers_dependent_limitations(constraints, expected):
    request = AnalysisRequest(
        objective=AnalysisObjective.GET,
        metrics=(AnalysisMetric.PERFORMANCE,),
        universe="santé",
        end_date=date(2026, 9, 24),
        horizons=(AnalysisHorizon.YEAR_TO_DATE,),
        constraints=constraints,
        unresolved=("L’indice ou l’univers géographique n’est pas précisé.",),
        ambiguity_scopes=(AmbiguityScope.INSTRUMENT,),
    )
    result = AnalysisRequestValidator().validate(request)
    assert result.status == expected
    assert "universe_capability_unsupported" not in result.issue_codes
    if constraints:
        assert "constraints_unsupported" in result.issue_codes
    else:
        assert "performance_reference_ambiguous" in result.issue_codes


def test_explicit_known_universe_does_not_become_provisional():
    request = AnalysisRequest(
        objective=AnalysisObjective.GET,
        metrics=(AnalysisMetric.PERFORMANCE,),
        universe="CAC 40",
        end_date=date(2026, 9, 24),
        horizons=(AnalysisHorizon.YEAR_TO_DATE,),
        unresolved=("Which currency?",),
    )
    result = AnalysisRequestValidator().validate(request)
    assert result.status == RequestStatus.UNSUPPORTED
    assert "universe_capability_unsupported" in result.issue_codes
