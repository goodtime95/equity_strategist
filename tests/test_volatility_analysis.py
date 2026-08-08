from datetime import date

import pandas as pd
import pytest

from equity_strategist.compute.returns import ReturnMethod
from equity_strategist.domain.asset import Asset
from equity_strategist.domain.market_dataset import MarketDataset
from equity_strategist.domain.market_series import (
    MarketSeries,
    SeriesKind,
)
from equity_strategist.services.volatility_analysis import (
    VolatilityAnalysisService,
)


class FakeMarketDatasetService:
    def build_price_dataset(
        self,
        asset_queries: list[str],
        start_date: date,
        end_date: date,
        universe: str | None = None,
        use_adjusted_close: bool = True,
    ) -> MarketDataset:
        lvmh = Asset(
            symbol="MC.PA",
            name="LVMH",
            currency="EUR",
        )

        hermes = Asset(
            symbol="RMS.PA",
            name="Hermès",
            currency="EUR",
        )

        lvmh_series = MarketSeries(
            identifier="MC.PA",
            kind=SeriesKind.PRICE,
            values=pd.Series(
                [100.0, 102.0, 101.0, 103.0],
                index=pd.to_datetime(
                    [
                        "2020-01-01",
                        "2020-01-02",
                        "2020-01-03",
                        "2020-01-06",
                    ]
                ),
            ),
            unit="EUR",
            metadata={"asset": lvmh},
        )

        hermes_series = MarketSeries(
            identifier="RMS.PA",
            kind=SeriesKind.PRICE,
            values=pd.Series(
                [100.0, 110.0, 95.0, 115.0],
                index=pd.to_datetime(
                    [
                        "2020-01-01",
                        "2020-01-02",
                        "2020-01-03",
                        "2020-01-06",
                    ]
                ),
            ),
            unit="EUR",
            metadata={"asset": hermes},
        )

        return MarketDataset(
            series_by_symbol={
                "MC.PA": lvmh_series,
                "RMS.PA": hermes_series,
            },
            universe=universe,
        )


def test_compare_volatility_ranks_assets() -> None:
    service = VolatilityAnalysisService(
        market_dataset_service=FakeMarketDatasetService()
    )

    result = service.compare(
        asset_queries=["LVMH", "Hermès"],
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 6),
        annualization_factor=252,
        return_method=ReturnMethod.LOG,
    )

    assert len(result.items) == 2
    assert result.items[0].symbol == "RMS.PA"
    assert result.items[1].symbol == "MC.PA"
    assert result.items[0].volatility > result.items[1].volatility


def test_compare_volatility_requires_two_assets() -> None:
    service = VolatilityAnalysisService(
        market_dataset_service=FakeMarketDatasetService()
    )

    with pytest.raises(
        ValueError,
        match="at least two assets",
    ):
        service.compare(
            asset_queries=["LVMH"],
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 6),
        )
