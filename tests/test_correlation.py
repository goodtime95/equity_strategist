import pandas as pd
import pytest

from equity_strategist.compute.correlation import (
    compute_correlation,
    compute_rolling_correlation,
)
from equity_strategist.domain.market_series import (
    MarketSeries,
    SeriesKind,
)


def build_first_return_series() -> MarketSeries:
    values = pd.Series(
        [0.01, 0.02, -0.01, 0.03],
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
        identifier="FIRST",
        kind=SeriesKind.RETURN,
        values=values,
        unit="decimal",
    )


def build_second_return_series() -> MarketSeries:
    values = pd.Series(
        [0.04, -0.02, 0.06, 0.01],
        index=pd.to_datetime(
            [
                "2020-01-03",
                "2020-01-06",
                "2020-01-07",
                "2020-01-08",
            ]
        ),
    )

    return MarketSeries(
        identifier="SECOND",
        kind=SeriesKind.RETURN,
        values=values,
        unit="decimal",
    )


def test_compute_correlation_aligns_common_dates() -> None:
    first = build_first_return_series()
    second = build_second_return_series()

    result = compute_correlation(
        first_series=first,
        second_series=second,
    )

    common_dates = pd.to_datetime(
        [
            "2020-01-03",
            "2020-01-06",
            "2020-01-07",
        ]
    )

    expected = first.values.loc[common_dates].corr(second.values.loc[common_dates])

    assert result == pytest.approx(expected)


def test_compute_rolling_correlation() -> None:
    first = build_first_return_series()
    second = build_second_return_series()

    result = compute_rolling_correlation(
        first_series=first,
        second_series=second,
        window=2,
    )

    assert result.kind == SeriesKind.CORRELATION
    assert result.unit == "decimal"
    assert result.observation_count == 2
    assert result.metadata["window"] == 2
    assert result.metadata["method"] == "pearson"


def test_correlation_requires_return_series() -> None:
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
        identifier="PRICE",
        kind=SeriesKind.PRICE,
        values=values,
        unit="EUR",
    )

    with pytest.raises(
        ValueError,
        match="require return series",
    ):
        compute_correlation(
            first_series=price_series,
            second_series=build_second_return_series(),
        )


def test_correlation_rejects_insufficient_overlap() -> None:
    first = build_first_return_series()

    second = MarketSeries(
        identifier="SECOND",
        kind=SeriesKind.RETURN,
        values=pd.Series(
            [0.01],
            index=pd.to_datetime(["2020-01-07"]),
        ),
        unit="decimal",
    )

    with pytest.raises(
        ValueError,
        match="insufficient overlapping observations",
    ):
        compute_correlation(
            first_series=first,
            second_series=second,
        )


def test_rolling_correlation_rejects_large_window() -> None:
    with pytest.raises(
        ValueError,
        match="cannot exceed",
    ):
        compute_rolling_correlation(
            first_series=build_first_return_series(),
            second_series=build_second_return_series(),
            window=10,
        )
