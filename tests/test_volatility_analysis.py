from datetime import date

import pandas as pd
import pytest

from equity_strategist.compute.returns import ReturnMethod
from equity_strategist.domain.asset import Asset
from equity_strategist.domain.market_series import (
    MarketSeries,
    SeriesKind,
)
from equity_strategist.services.volatility_analysis import (
    VolatilityAnalysisService,
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
        if asset_query == "LVMH":
            asset = Asset(
                symbol="MC.PA",
                name="LVMH",
                currency="EUR",
            )
            values = [100.0, 102.0, 101.0, 103.0]
        else:
            asset = Asset(
                symbol="RMS.PA",
                name="Hermès",
                currency="EUR",
            )
            values = [100.0, 110.0, 95.0, 115.0]

        return MarketSeries(
            identifier=asset.symbol,
            kind=SeriesKind.PRICE,
            values=pd.Series(
                values,
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
            metadata={"asset": asset},
        )


def test_compare_volatility_ranks_assets() -> None:
    service = VolatilityAnalysisService(market_series_service=FakeMarketSeriesService())

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
    service = VolatilityAnalysisService(market_series_service=FakeMarketSeriesService())

    with pytest.raises(
        ValueError,
        match="at least two assets",
    ):
        service.compare(
            asset_queries=["LVMH"],
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 6),
        )
