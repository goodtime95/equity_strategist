from datetime import date

import pandas as pd
import pytest

from equity_strategist.domain.asset import Asset
from equity_strategist.domain.market_dataset import MarketDataset
from equity_strategist.domain.market_series import (
    MarketSeries,
    SeriesKind,
)
from equity_strategist.services.drawdown_analysis import (
    DrawdownAnalysisService,
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

        index = pd.to_datetime(
            [
                "2020-01-01",
                "2020-01-02",
                "2020-01-03",
                "2020-01-06",
                "2020-01-07",
            ]
        )

        return MarketDataset(
            series_by_symbol={
                "MC.PA": MarketSeries(
                    identifier="MC.PA",
                    kind=SeriesKind.PRICE,
                    values=pd.Series(
                        [100.0, 120.0, 90.0, 80.0, 100.0],
                        index=index,
                    ),
                    unit="EUR",
                    metadata={"asset": lvmh},
                ),
                "RMS.PA": MarketSeries(
                    identifier="RMS.PA",
                    kind=SeriesKind.PRICE,
                    values=pd.Series(
                        [100.0, 110.0, 100.0, 95.0, 108.0],
                        index=index,
                    ),
                    unit="EUR",
                    metadata={"asset": hermes},
                ),
            }
        )


def test_drawdown_analysis_ranks_worst_drawdown_first() -> None:
    service = DrawdownAnalysisService(market_dataset_service=FakeMarketDatasetService())

    result = service.compare(
        asset_queries=["LVMH", "Hermès"],
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 7),
    )

    assert len(result.items) == 2
    assert result.items[0].symbol == "MC.PA"
    assert result.items[1].symbol == "RMS.PA"
    assert result.items[0].maximum_drawdown < result.items[1].maximum_drawdown


def test_drawdown_analysis_requires_two_assets() -> None:
    service = DrawdownAnalysisService(market_dataset_service=FakeMarketDatasetService())

    with pytest.raises(
        ValueError,
        match="at least two assets",
    ):
        service.compare(
            asset_queries=["LVMH"],
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 7),
        )
