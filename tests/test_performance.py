from datetime import date

import pandas as pd
import pytest

from equity_strategist.compute.performance import (
    compute_annualized_performance,
    compute_cumulative_performance,
    compute_period_performance,
    compute_total_performance,
)
from equity_strategist.domain.market_series import (
    MarketSeries,
    SeriesKind,
)


def extract_price_series() -> MarketSeries:
    values = pd.Series(
        [100.0, 110.0, 121.0],
        index=pd.to_datetime(
            [
                "2020-01-01",
                "2020-07-01",
                "2021-01-01",
            ]
        ),
    )

    return MarketSeries(
        identifier="TEST",
        kind=SeriesKind.PRICE,
        values=values,
        unit="EUR",
    )


def test_compute_total_performance() -> None:
    result = compute_total_performance(extract_price_series())

    assert result == pytest.approx(0.21)


def test_compute_period_performance() -> None:
    result = compute_period_performance(
        extract_price_series(),
        start_date=date(2020, 1, 1),
        end_date=date(2020, 7, 1),
    )

    assert result == pytest.approx(0.10)


def test_compute_period_performance_uses_available_dates() -> None:
    result = compute_period_performance(
        extract_price_series(),
        start_date=date(2020, 1, 2),
        end_date=date(2021, 1, 1),
    )

    assert result == pytest.approx(0.10)


def test_compute_annualized_performance() -> None:
    result = compute_annualized_performance(extract_price_series())

    assert result == pytest.approx(
        0.21,
        abs=0.002,
    )


def test_compute_cumulative_performance() -> None:
    result = compute_cumulative_performance(extract_price_series())

    assert result.kind == SeriesKind.RETURN
    assert result.unit == "decimal"
    assert result.values.iloc[0] == pytest.approx(0.0)
    assert result.values.iloc[1] == pytest.approx(0.10)
    assert result.values.iloc[2] == pytest.approx(0.21)
    assert result.metadata["calculation"] == ("cumulative_performance")


def test_performance_requires_price_series() -> None:
    values = pd.Series(
        [0.01, 0.02],
        index=pd.to_datetime(
            [
                "2020-01-01",
                "2020-01-02",
            ]
        ),
    )

    return_series = MarketSeries(
        identifier="TEST",
        kind=SeriesKind.RETURN,
        values=values,
        unit="decimal",
    )

    with pytest.raises(
        ValueError,
        match="require a price series",
    ):
        compute_total_performance(return_series)


def test_period_performance_rejects_invalid_dates() -> None:
    with pytest.raises(
        ValueError,
        match="start_date",
    ):
        compute_period_performance(
            extract_price_series(),
            start_date=date(2021, 1, 1),
            end_date=date(2020, 1, 1),
        )
