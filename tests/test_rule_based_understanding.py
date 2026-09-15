from datetime import date

import pytest

from equity_strategist.domain.analysis_request import (
    AnalysisHorizon,
    AnalysisMetric,
    AnalysisObjective,
    PerformanceMeasure,
    RankingDirection,
)
from equity_strategist.domain.request_validation import RequestStatus
from equity_strategist.domain.universe import (
    Universe,
    UniverseType,
)
from equity_strategist.strategists.validator import AnalysisRequestValidator
from equity_strategist.understanding.rule_based import (
    RuleBasedUnderstanding,
    UnderstandingError,
)
from equity_strategist.universe_registry.registry import (
    UniverseRegistry,
)


# Helper commun à tous les tests
def build_understanding() -> RuleBasedUnderstanding:
    registry = UniverseRegistry(
        [
            Universe(
                name="Luxury Europe",
                universe_type=UniverseType.STATIC,
                asset_queries=(
                    "LVMH",
                    "Hermès",
                ),
                aliases=(
                    "Luxury",
                    "European Luxury",
                ),
            )
        ]
    )

    return RuleBasedUnderstanding(
        universe_registry=registry,
    )


def test_understand_volatility_comparison() -> None:
    understanding = build_understanding()

    request = understanding.understand(
        "Compare la volatilité de LVMH et Hermès sur les 2 dernières années",
        today=date(2026, 8, 8),
    )

    assert request.objective == AnalysisObjective.COMPARE
    assert request.metrics == (AnalysisMetric.VOLATILITY,)
    assert request.assets == (
        "LVMH",
        "Hermès",
    )
    assert request.start_date == date(2024, 8, 8)
    assert request.end_date == date(2026, 8, 8)


def test_understand_period_since_year() -> None:
    understanding = build_understanding()

    request = understanding.understand(
        "Compare la volatilité de LVMH et ASML depuis 2022",
        today=date(2026, 8, 8),
    )

    assert request.start_date == date(2022, 1, 1)
    assert request.end_date == date(2026, 8, 8)


def test_understand_price_on_iso_date() -> None:
    understanding = build_understanding()

    request = understanding.understand(
        "Quel était le prix de LVMH le 2020-03-15 ?",
        today=date(2026, 8, 8),
    )

    assert request.objective == AnalysisObjective.GET
    assert request.metrics == (AnalysisMetric.PRICE,)
    assert request.assets == ("LVMH",)
    assert request.target_date == date(2020, 3, 15)


def test_understand_unknown_metric_fails() -> None:
    understanding = build_understanding()

    with pytest.raises(
        UnderstandingError,
        match="metric",
    ):
        understanding.understand(
            "Compare LVMH et Hermès",
            today=date(2026, 8, 8),
        )


def test_understand_unknown_asset_fails() -> None:
    understanding = build_understanding()

    with pytest.raises(
        UnderstandingError,
        match="assets",
    ):
        understanding.understand(
            "Compare la volatilité de Société Générale et BNP",
            today=date(2026, 8, 8),
        )


def test_understand_correlation_analysis() -> None:
    understanding = build_understanding()

    request = understanding.understand(
        "Analyse les corrélations entre LVMH, Hermès "
        "et ASML sur les 2 dernières années",
        today=date(2026, 8, 8),
    )

    assert request.objective == AnalysisObjective.ANALYZE
    assert request.metrics == (AnalysisMetric.CORRELATION,)
    assert request.assets == (
        "LVMH",
        "Hermès",
        "ASML",
    )
    assert request.start_date == date(2024, 8, 8)
    assert request.end_date == date(2026, 8, 8)


def test_understand_drawdown_comparison() -> None:
    understanding = build_understanding()

    request = understanding.understand(
        "Compare le drawdown de LVMH, Hermès et ASML sur les 2 dernières années",
        today=date(2026, 8, 9),
    )

    assert request.objective == AnalysisObjective.COMPARE
    assert request.metrics == (AnalysisMetric.DRAWDOWN,)
    assert request.assets == (
        "LVMH",
        "Hermès",
        "ASML",
    )
    assert request.start_date == date(2024, 8, 9)
    assert request.end_date == date(2026, 8, 9)


def test_understand_performance_ranking() -> None:
    understanding = build_understanding()

    request = understanding.understand(
        "Classe LVMH, Hermès et ASML par performance sur les 2 dernières années",
        today=date(2026, 8, 9),
    )

    assert request.objective == AnalysisObjective.RANK
    assert request.metrics == (AnalysisMetric.PERFORMANCE,)
    assert request.assets == ("LVMH", "Hermès", "ASML")
    assert request.start_date == date(2024, 8, 9)
    assert request.end_date == date(2026, 8, 9)


def test_understand_lowest_top_n_ranking() -> None:
    request = build_understanding().understand(
        "Top 2 des moins volatiles entre LVMH, Hermès et ASML "
        "sur les 2 dernières années",
        today=date(2026, 8, 9),
    )

    assert request.objective == AnalysisObjective.RANK
    assert request.ranking_direction == RankingDirection.LOWEST
    assert request.top_n == 2
    assert request.assets == (
        "LVMH",
        "Hermès",
        "ASML",
    )
    assert request.start_date == date(2024, 8, 9)
    assert request.end_date == date(2026, 8, 9)


def test_understand_performance_ranking_from_universe() -> None:
    understanding = build_understanding()

    request = understanding.understand(
        "Classe Luxury Europe par performance sur les 2 dernières années",
        today=date(2026, 8, 10),
    )

    assert request.objective == AnalysisObjective.RANK
    assert request.metrics == (AnalysisMetric.PERFORMANCE,)
    assert request.assets == ()
    assert request.universe == "Luxury Europe"


def test_understand_preserves_explicit_assets_with_universe() -> None:
    request = build_understanding().understand(
        "Classe LVMH et Hermès dans Luxury Europe par performance "
        "sur les 2 dernières années",
        today=date(2026, 8, 10),
    )

    assert request.assets == ("LVMH", "Hermès")
    assert request.universe == "Luxury Europe"

    validation = AnalysisRequestValidator().validate(request)

    assert validation.status == RequestStatus.NEEDS_CLARIFICATION
    assert any("specify one asset source" in issue for issue in validation.issues)


def test_understand_minimal_performance_horizon_and_measure() -> None:
    request = build_understanding().understand(
        "Compare LVMH et Hermès en annualized performance over 1M and 3Y",
        today=date(2026, 9, 13),
    )

    assert request.performance_measure == PerformanceMeasure.ANNUALIZED
    assert request.horizons == (
        AnalysisHorizon.ONE_MONTH,
        AnalysisHorizon.THREE_YEARS,
    )
    assert request.start_date is None
    assert request.end_date == date(2026, 9, 13)


def test_understand_minimal_relative_benchmark() -> None:
    request = build_understanding().understand(
        "Compare LVMH et Hermès by relative performance relative to S&P 500 over 1Y",
        today=date(2026, 9, 13),
    )

    assert request.performance_measure == PerformanceMeasure.RELATIVE
    assert request.benchmark == "S&P 500"


@pytest.mark.parametrize("anchor", ["December 31, 2024", "2024-12-31"])
def test_historical_horizon_anchor_requires_clarification(anchor: str) -> None:
    request = build_understanding().understand(
        f"Compare LVMH and Hermes YTD performance as of {anchor}",
        today=date(2026, 9, 15),
    )
    assert request.end_date is None
    assert request.unresolved
    assert (
        AnalysisRequestValidator().validate(request).status
        == RequestStatus.NEEDS_CLARIFICATION
    )


@pytest.mark.parametrize(
    "horizons",
    ["1m and 2y", "1m and two years", "1m and 12m", "1m and 2 weeks", "1m and 1 y"],
)
def test_incomplete_horizon_list_requires_clarification(horizons: str) -> None:
    request = build_understanding().understand(
        f"Compare LVMH and Hermes performance over {horizons}",
        today=date(2026, 9, 15),
    )
    assert request.unresolved
    assert (
        AnalysisRequestValidator().validate(request).status
        == RequestStatus.NEEDS_CLARIFICATION
    )


@pytest.mark.parametrize("period", ["1m and two years", "2y depuis 2022"])
def test_unparsed_horizons_without_over_are_not_executed(period: str) -> None:
    request = build_understanding().understand(
        f"Compare LVMH and Hermes performance {period}",
        today=date(2026, 9, 15),
    )
    assert request.unresolved
    assert (
        AnalysisRequestValidator().validate(request).status
        == RequestStatus.NEEDS_CLARIFICATION
    )
