from datetime import date

import pytest

from equity_strategist.domain.analysis_request import (
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
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


def test_analysis_request_requires_asset_or_universe() -> None:
    with pytest.raises(
        ValueError,
        match="asset or universe",
    ):
        AnalysisRequest(
            objective=AnalysisObjective.COMPARE,
            metrics=(AnalysisMetric.VOLATILITY,),
        )


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
