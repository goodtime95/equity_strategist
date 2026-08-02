import math

import pandas as pd
import pytest

from equity_strategist.compute.volatility import (
    compute_rolling_volatility,
    compute_volatility,
)
from equity_strategist.domain.market_series import (
    MarketSeries,
    SeriesKind,
)


def build_return_series() -> MarketSeries:
    values = pd.Series(
        [0.01, -0.02, 0.015, 0.005],
        index=pd.to_datetime(
            [
                "2020-01-02",
                "2020-01-03",
                "2020-01-06",
                "2020-01-07",
            ]
        ),
    )

    return MarketSeries(
        identifier="TEST",
        kind=SeriesKind.RETURN,
        values=values,
        unit="decimal",
    )


def test_compute_volatility() -> None:
    return_series = build_return_series()

    result = compute_volatility(
        return_series,
        annualization_factor=252,
    )

    expected = return_series.values.std(ddof=1) * math.sqrt(252)

    assert result == pytest.approx(expected)


def test_compute_volatility_without_annualization() -> None:
    return_series = build_return_series()

    result = compute_volatility(
        return_series,
        annualization_factor=1,
    )

    assert result == pytest.approx(return_series.values.std(ddof=1))


def test_compute_rolling_volatility() -> None:
    return_series = build_return_series()

    result = compute_rolling_volatility(
        return_series=return_series,
        window=3,
        annualization_factor=252,
    )

    expected = return_series.values.rolling(window=3).std(ddof=1).dropna() * math.sqrt(
        252
    )

    assert result.kind == SeriesKind.VOLATILITY
    assert result.unit == "decimal"
    assert result.observation_count == 2
    assert result.values.iloc[0] == pytest.approx(expected.iloc[0])
    assert result.values.iloc[1] == pytest.approx(expected.iloc[1])
    assert result.metadata["window"] == 3
    assert result.metadata["annualization_factor"] == 252


def test_volatility_requires_return_series() -> None:
    values = pd.Series(
        [100.0, 101.0],
        index=pd.to_datetime(
            [
                "2020-01-01",
                "2020-01-02",
            ]
        ),
    )

    price_series = MarketSeries(
        identifier="TEST",
        kind=SeriesKind.PRICE,
        values=values,
        unit="EUR",
    )

    with pytest.raises(
        ValueError,
        match="require a return series",
    ):
        compute_volatility(price_series)


def test_rolling_volatility_rejects_large_window() -> None:
    with pytest.raises(
        ValueError,
        match="cannot exceed",
    ):
        compute_rolling_volatility(
            return_series=build_return_series(),
            window=10,
        )


def test_volatility_rejects_invalid_annualization_factor() -> None:
    with pytest.raises(
        ValueError,
        match="strictly positive",
    ):
        compute_volatility(
            return_series=build_return_series(),
            annualization_factor=0,
        )
