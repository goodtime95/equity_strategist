from datetime import date

import pandas as pd
import pytest

from equity_strategist.domain.asset import Asset
from equity_strategist.domain.market_dataset import MarketDataset
from equity_strategist.domain.market_series import (
    MarketSeries,
    SeriesKind,
)
from equity_strategist.services.correlation_analysis import (
    CorrelationAnalysisService,
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
                        [100.0, 102.0, 101.0, 103.0, 104.0],
                        index=index,
                    ),
                    unit="EUR",
                    metadata={"asset": lvmh},
                ),
                "RMS.PA": MarketSeries(
                    identifier="RMS.PA",
                    kind=SeriesKind.PRICE,
                    values=pd.Series(
                        [100.0, 103.0, 102.0, 105.0, 106.0],
                        index=index,
                    ),
                    unit="EUR",
                    metadata={"asset": hermes},
                ),
                "ASML.AS": MarketSeries(
                    identifier="ASML.AS",
                    kind=SeriesKind.PRICE,
                    values=pd.Series(
                        [100.0, 98.0, 101.0, 99.0, 102.0],
                        index=index,
                    ),
                    unit="EUR",
                    metadata={"asset": asml},
                ),
            }
        )


def test_correlation_analysis_builds_all_pairs() -> None:
    service = CorrelationAnalysisService(
        market_dataset_service=FakeMarketDatasetService()
    )

    result = service.analyze(
        asset_queries=[
            "LVMH",
            "Hermès",
            "ASML",
        ],
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 7),
    )

    assert len(result.items) == 3

    pairs = {
        (
            item.first_symbol,
            item.second_symbol,
        )
        for item in result.items
    }

    assert pairs == {
        ("MC.PA", "RMS.PA"),
        ("MC.PA", "ASML.AS"),
        ("RMS.PA", "ASML.AS"),
    }


def test_correlation_analysis_requires_two_assets() -> None:
    service = CorrelationAnalysisService(
        market_dataset_service=FakeMarketDatasetService()
    )

    with pytest.raises(
        ValueError,
        match="at least two assets",
    ):
        service.analyze(
            asset_queries=["LVMH"],
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 7),
        )
