import pandas as pd
import pytest

from equity_strategist.domain.market_dataset import MarketDataset
from equity_strategist.domain.market_series import (
    MarketSeries,
    SeriesKind,
)


def build_series(symbol: str) -> MarketSeries:
    return MarketSeries(
        identifier=symbol,
        kind=SeriesKind.PRICE,
        values=pd.Series(
            [100.0, 101.0],
            index=pd.to_datetime(
                [
                    "2020-01-01",
                    "2020-01-02",
                ]
            ),
        ),
        unit="EUR",
    )


def test_market_dataset_contains_multiple_series() -> None:
    dataset = MarketDataset(
        series_by_symbol={
            "MC.PA": build_series("MC.PA"),
            "RMS.PA": build_series("RMS.PA"),
        },
        universe="TEST",
    )

    assert dataset.size == 2
    assert dataset.symbols == ("MC.PA", "RMS.PA")
    assert dataset.get("MC.PA").identifier == "MC.PA"


def test_market_dataset_rejects_empty_dataset() -> None:
    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):
        MarketDataset(series_by_symbol={})


def test_market_dataset_rejects_mismatched_key() -> None:
    with pytest.raises(
        ValueError,
        match="key must match",
    ):
        MarketDataset(
            series_by_symbol={
                "WRONG": build_series("MC.PA"),
            }
        )


def test_market_dataset_rejects_unknown_symbol() -> None:
    dataset = MarketDataset(
        series_by_symbol={
            "MC.PA": build_series("MC.PA"),
        }
    )

    with pytest.raises(
        KeyError,
        match="symbol not found",
    ):
        dataset.get("RMS.PA")
