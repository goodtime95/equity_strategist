import numpy as np
import pandas as pd
import pytest

from equity_strategist.compute.returns import (
    ReturnMethod,
    compute_returns,
)
from equity_strategist.domain.market_series import (
    MarketSeries,
    SeriesKind,
)


def build_price_series() -> MarketSeries:
    values = pd.Series(
        [100.0, 105.0, 102.9],
        index=pd.to_datetime(
            [
                "2020-01-01",
                "2020-01-02",
                "2020-01-03",
            ]
        ),
    )

    return MarketSeries(
        identifier="TEST",
        kind=SeriesKind.PRICE,
        values=values,
        unit="EUR",
    )


def test_compute_simple_returns() -> None:
    price_series = build_price_series()

    returns = compute_returns(
        price_series,
        method=ReturnMethod.SIMPLE,
    )

    assert returns.kind == SeriesKind.RETURN
    assert returns.unit == "decimal"
    assert returns.observation_count == 2
    assert returns.values.iloc[0] == pytest.approx(0.05)
    assert returns.values.iloc[1] == pytest.approx(-0.02)
    assert returns.metadata["return_method"] == "simple"


def test_compute_log_returns() -> None:
    price_series = build_price_series()

    returns = compute_returns(
        price_series,
        method=ReturnMethod.LOG,
    )

    assert returns.values.iloc[0] == pytest.approx(np.log(105.0 / 100.0))
    assert returns.values.iloc[1] == pytest.approx(np.log(102.9 / 105.0))
    assert returns.metadata["return_method"] == "log"


def test_compute_returns_requires_price_series() -> None:
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
        match="requires a price series",
    ):
        compute_returns(return_series)


def test_compute_returns_requires_two_observations() -> None:
    values = pd.Series(
        [100.0],
        index=pd.to_datetime(["2020-01-01"]),
    )

    price_series = MarketSeries(
        identifier="TEST",
        kind=SeriesKind.PRICE,
        values=values,
        unit="EUR",
    )

    with pytest.raises(
        ValueError,
        match="at least two",
    ):
        compute_returns(price_series)


def test_compute_returns_rejects_non_positive_prices() -> None:
    values = pd.Series(
        [100.0, 0.0],
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
        match="strictly positive",
    ):
        compute_returns(price_series)
