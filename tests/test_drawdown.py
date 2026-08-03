import pandas as pd
import pytest

from equity_strategist.compute.drawdown import (
    compute_drawdown_series,
    compute_maximum_drawdown,
)
from equity_strategist.domain.market_series import (
    MarketSeries,
    SeriesKind,
)


def build_recovered_price_series() -> MarketSeries:
    values = pd.Series(
        [100.0, 120.0, 90.0, 80.0, 100.0, 120.0, 125.0],
        index=pd.to_datetime(
            [
                "2020-01-01",
                "2020-01-02",
                "2020-01-03",
                "2020-01-06",
                "2020-01-07",
                "2020-01-08",
                "2020-01-09",
            ]
        ),
    )

    return MarketSeries(
        identifier="TEST",
        kind=SeriesKind.PRICE,
        values=values,
        unit="EUR",
    )


def test_compute_drawdown_series() -> None:
    result = compute_drawdown_series(build_recovered_price_series())

    assert result.kind == SeriesKind.DRAWDOWN
    assert result.unit == "decimal"
    assert result.values.iloc[0] == pytest.approx(0.0)
    assert result.values.iloc[1] == pytest.approx(0.0)
    assert result.values.iloc[2] == pytest.approx(-0.25)
    assert result.values.iloc[3] == pytest.approx(80.0 / 120.0 - 1.0)


def test_compute_maximum_drawdown() -> None:
    result = compute_maximum_drawdown(build_recovered_price_series())

    assert result.maximum_drawdown == pytest.approx(80.0 / 120.0 - 1.0)
    assert result.peak_date == pd.Timestamp("2020-01-02")
    assert result.trough_date == pd.Timestamp("2020-01-06")
    assert result.recovery_date == pd.Timestamp("2020-01-08")


def test_compute_maximum_drawdown_without_recovery() -> None:
    values = pd.Series(
        [100.0, 120.0, 90.0, 80.0, 100.0],
        index=pd.to_datetime(
            [
                "2020-01-01",
                "2020-01-02",
                "2020-01-03",
                "2020-01-06",
                "2020-01-07",
            ]
        ),
    )

    price_series = MarketSeries(
        identifier="TEST",
        kind=SeriesKind.PRICE,
        values=values,
        unit="EUR",
    )

    result = compute_maximum_drawdown(price_series)

    assert result.recovery_date is None


def test_drawdown_requires_price_series() -> None:
    return_series = MarketSeries(
        identifier="TEST",
        kind=SeriesKind.RETURN,
        values=pd.Series(
            [0.01, -0.02],
            index=pd.to_datetime(
                [
                    "2020-01-01",
                    "2020-01-02",
                ]
            ),
        ),
        unit="decimal",
    )

    with pytest.raises(
        ValueError,
        match="require a price series",
    ):
        compute_drawdown_series(return_series)
