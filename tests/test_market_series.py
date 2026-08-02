import pandas as pd
import pytest

from equity_strategist.domain.market_series import (
    MarketSeries,
    SeriesKind,
)


def test_market_series_sorts_observations() -> None:
    values = pd.Series(
        [102.0, 100.0, 101.0],
        index=pd.to_datetime(
            [
                "2020-03-17",
                "2020-03-13",
                "2020-03-16",
            ]
        ),
    )

    series = MarketSeries(
        identifier="MC.PA",
        kind=SeriesKind.PRICE,
        values=values,
        unit="EUR",
    )

    assert series.start_date == pd.Timestamp("2020-03-13")
    assert series.end_date == pd.Timestamp("2020-03-17")
    assert series.observation_count == 3
    assert series.values.iloc[0] == 100.0


def test_market_series_rejects_duplicate_dates() -> None:
    values = pd.Series(
        [100.0, 101.0],
        index=pd.to_datetime(
            [
                "2020-03-13",
                "2020-03-13",
            ]
        ),
    )

    with pytest.raises(ValueError, match="duplicate dates"):
        MarketSeries(
            identifier="MC.PA",
            kind=SeriesKind.PRICE,
            values=values,
            unit="EUR",
        )


def test_market_series_rejects_missing_values() -> None:
    values = pd.Series(
        [100.0, None],
        index=pd.to_datetime(
            [
                "2020-03-13",
                "2020-03-16",
            ]
        ),
    )

    with pytest.raises(ValueError, match="missing observations"):
        MarketSeries(
            identifier="MC.PA",
            kind=SeriesKind.PRICE,
            values=values,
            unit="EUR",
        )
