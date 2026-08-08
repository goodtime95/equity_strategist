from datetime import date

import pytest

from equity_strategist.domain.analysis_request import (
    AnalysisIntent,
    AnalysisRequest,
)


def test_analysis_request() -> None:
    request = AnalysisRequest(
        intent=AnalysisIntent.COMPARE_VOLATILITY,
        assets=("LVMH", "Hermès"),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
    )

    assert request.intent == AnalysisIntent.COMPARE_VOLATILITY
    assert request.assets == ("LVMH", "Hermès")


def test_analysis_request_requires_asset() -> None:
    with pytest.raises(
        ValueError,
        match="at least one asset",
    ):
        AnalysisRequest(
            intent=AnalysisIntent.COMPARE_VOLATILITY,
            assets=(),
        )


def test_analysis_request_rejects_invalid_period() -> None:
    with pytest.raises(
        ValueError,
        match="start_date",
    ):
        AnalysisRequest(
            intent=AnalysisIntent.COMPARE_VOLATILITY,
            assets=("LVMH", "Hermès"),
            start_date=date(2025, 1, 1),
            end_date=date(2024, 1, 1),
        )
