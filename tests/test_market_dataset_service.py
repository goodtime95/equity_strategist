from datetime import date

import pandas as pd
import pytest

from equity_strategist.domain.asset import Asset
from equity_strategist.domain.market_series import (
    MarketSeries,
    SeriesKind,
)
from equity_strategist.services.market_dataset import (
    MarketDatasetService,
)


class FakeMarketSeriesService:
    def get_price_series(
        self,
        asset_query: str,
        start_date: date,
        end_date: date,
        preferred_exchange: str | None = None,
        preferred_currency: str | None = None,
        use_adjusted_close: bool = True,
    ) -> MarketSeries:
        mapping = {
            "LVMH": Asset(
                symbol="MC.PA",
                name="LVMH",
                currency="EUR",
            ),
            "Hermès": Asset(
                symbol="RMS.PA",
                name="Hermès",
                currency="EUR",
            ),
        }

        asset = mapping[asset_query]

        return MarketSeries(
            identifier=asset.symbol,
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
            unit=asset.currency or "unknown",
            metadata={"asset": asset},
        )


def test_build_price_dataset() -> None:
    service = MarketDatasetService(market_series_service=FakeMarketSeriesService())

    dataset = service.build_price_dataset(
        asset_queries=["LVMH", "Hermès"],
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 2),
        universe="TEST",
    )

    assert dataset.size == 2
    assert dataset.universe == "TEST"
    assert set(dataset.symbols) == {
        "MC.PA",
        "RMS.PA",
    }


def test_build_price_dataset_requires_assets() -> None:
    service = MarketDatasetService(market_series_service=FakeMarketSeriesService())

    with pytest.raises(
        ValueError,
        match="at least one asset",
    ):
        service.build_price_dataset(
            asset_queries=[],
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 2),
        )
