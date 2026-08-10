from datetime import date

import pytest

from equity_strategist.domain.analysis_request import (
    AnalysisMetric,
    AnalysisObjective,
)
from equity_strategist.domain.universe import (
    Universe,
    UniverseType,
)
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
