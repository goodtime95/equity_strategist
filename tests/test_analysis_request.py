from datetime import date

import pytest

from equity_strategist.domain.analysis_request import (
    AnalysisHorizon,
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
    PerformanceMeasure,
)


def test_analysis_request() -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(AnalysisMetric.VOLATILITY,),
        assets=("LVMH", "Hermès"),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
    )

    assert request.objective == AnalysisObjective.COMPARE
    assert request.metrics == (AnalysisMetric.VOLATILITY,)
    assert request.assets == ("LVMH", "Hermès")


def test_analysis_request_allows_missing_asset_and_universe() -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(AnalysisMetric.PERFORMANCE,),
    )

    assert request.assets == ()
    assert request.universe is None


def test_analysis_request_accepts_universe_without_assets() -> None:
    request = AnalysisRequest(
        objective=AnalysisObjective.RANK,
        metrics=(AnalysisMetric.PERFORMANCE,),
        universe="CAC 40",
    )

    assert request.assets == ()
    assert request.universe == "CAC 40"


def test_analysis_request_rejects_invalid_period() -> None:
    with pytest.raises(
        ValueError,
        match="start_date",
    ):
        AnalysisRequest(
            objective=AnalysisObjective.COMPARE,
            metrics=(AnalysisMetric.VOLATILITY,),
            assets=("LVMH", "Hermès"),
            start_date=date(2025, 1, 1),
            end_date=date(2024, 1, 1),
        )


@pytest.mark.parametrize("ranking_direction", ["highest", "sideways", 1])
def test_analysis_request_rejects_invalid_ranking_direction(
    ranking_direction: object,
) -> None:
    with pytest.raises(TypeError, match="RankingDirection"):
        AnalysisRequest(
            objective=AnalysisObjective.RANK,
            ranking_direction=ranking_direction,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("top_n", [1.5, "2", True])
def test_analysis_request_rejects_non_integer_top_n(top_n: object) -> None:
    with pytest.raises(TypeError, match="integer"):
        AnalysisRequest(
            objective=AnalysisObjective.RANK,
            top_n=top_n,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("top_n", [0, -1])
def test_analysis_request_rejects_non_positive_top_n(top_n: int) -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        AnalysisRequest(
            objective=AnalysisObjective.RANK,
            top_n=top_n,
        )


def test_analysis_request_preserves_previous_positional_arguments() -> None:
    request = AnalysisRequest(
        AnalysisObjective.COMPARE,
        (AnalysisMetric.PERFORMANCE,),
        ("LVMH", "Hermès"),
        None,
        date(2024, 1, 1),
        date(2025, 1, 1),
        None,
        None,
        None,
        ("EUR only",),
        "Compare the assets",
        ("clarify risk",),
    )

    assert request.constraints == ("EUR only",)
    assert request.user_context == "Compare the assets"
    assert request.unresolved == ("clarify risk",)
    assert request.ranking_direction is None
    assert request.top_n is None
    assert request.performance_measure == PerformanceMeasure.TOTAL
    assert request.horizons == ()


@pytest.mark.parametrize("measure", ["total", "annualized", object()])
def test_analysis_request_rejects_invalid_performance_measure(measure: object) -> None:
    with pytest.raises(TypeError, match="PerformanceMeasure"):
        AnalysisRequest(
            objective=AnalysisObjective.COMPARE,
            performance_measure=measure,  # type: ignore[arg-type]
        )


def test_analysis_request_rejects_invalid_or_duplicate_horizons() -> None:
    with pytest.raises(TypeError, match="AnalysisHorizon"):
        AnalysisRequest(
            objective=AnalysisObjective.COMPARE,
            horizons=("1m",),  # type: ignore[arg-type]
        )

    with pytest.raises(ValueError, match="duplicates"):
        AnalysisRequest(
            objective=AnalysisObjective.COMPARE,
            horizons=(AnalysisHorizon.ONE_MONTH, AnalysisHorizon.ONE_MONTH),
        )


def test_analysis_request_appends_new_positional_fields() -> None:
    request = AnalysisRequest(
        AnalysisObjective.COMPARE,
        (AnalysisMetric.PERFORMANCE,),
        ("LVMH", "Hermès"),
        None,
        None,
        date(2025, 1, 5),
        None,
        None,
        "S&P 500",
        (),
        None,
        (),
        None,
        None,
        PerformanceMeasure.RELATIVE,
        (AnalysisHorizon.ONE_MONTH,),
    )

    assert request.performance_measure == PerformanceMeasure.RELATIVE
    assert request.horizons == (AnalysisHorizon.ONE_MONTH,)
