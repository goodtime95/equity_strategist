from datetime import date

import pandas as pd
import pytest

from equity_strategist.domain.asset import Asset
from equity_strategist.domain.market_dataset import (
    MarketDataset,
)
from equity_strategist.domain.market_series import (
    MarketSeries,
    SeriesKind,
)
from equity_strategist.services.ranking_analysis import (
    RankingAnalysisService,
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

        asml = Asset(
            symbol="ASML.AS",
            name="ASML",
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
                        [100.0, 105.0, 110.0, 115.0, 120.0],
                        index=index,
                    ),
                    unit="EUR",
                    metadata={"asset": lvmh},
                ),
                "RMS.PA": MarketSeries(
                    identifier="RMS.PA",
                    kind=SeriesKind.PRICE,
                    values=pd.Series(
                        [100.0, 102.0, 104.0, 106.0, 110.0],
                        index=index,
                    ),
                    unit="EUR",
                    metadata={"asset": hermes},
                ),
                "ASML.AS": MarketSeries(
                    identifier="ASML.AS",
                    kind=SeriesKind.PRICE,
                    values=pd.Series(
                        [100.0, 98.0, 101.0, 99.0, 105.0],
                        index=index,
                    ),
                    unit="EUR",
                    metadata={"asset": asml},
                ),
            }
        )


def test_rank_performance_orders_assets() -> None:
    service = RankingAnalysisService(market_dataset_service=FakeMarketDatasetService())

    result = service.rank_performance(
        asset_queries=[
            "LVMH",
            "Hermès",
            "ASML",
        ],
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 7),
    )

    assert len(result.items) == 3

    assert result.items[0].rank == 1
    assert result.items[1].rank == 2
    assert result.items[2].rank == 3

    assert result.items[0].symbol == "MC.PA"
    assert result.items[1].symbol == "RMS.PA"
    assert result.items[2].symbol == "ASML.AS"

    assert result.items[0].value >= result.items[1].value >= result.items[2].value


def test_rank_performance_requires_two_assets() -> None:
    service = RankingAnalysisService(market_dataset_service=FakeMarketDatasetService())

    with pytest.raises(
        ValueError,
        match="at least two assets",
    ):
        service.rank_performance(
            asset_queries=["LVMH"],
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 7),
        )


def test_rank_volatility() -> None:
    service = RankingAnalysisService(market_dataset_service=FakeMarketDatasetService())

    result = service.rank_volatility(
        asset_queries=[
            "LVMH",
            "Hermès",
            "ASML",
        ],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )

    assert result.metric == "volatility"

    assert tuple(item.symbol for item in result.items) == (
        "ASML.AS",
        "RMS.PA",
        "MC.PA",
    )

    assert result.items[0].value > result.items[1].value
    assert result.items[1].value > result.items[2].value
