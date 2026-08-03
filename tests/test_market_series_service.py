from datetime import date
from decimal import Decimal

import pytest

from equity_strategist.domain.asset import Asset
from equity_strategist.domain.market_series import SeriesKind
from equity_strategist.domain.observations import DailyPriceObservation
from equity_strategist.services.market_series import MarketSeriesService


class FakeAssetResolver:
    def resolve(
        self,
        query: str,
        preferred_currency: str | None = None,
        preferred_exchange: str | None = None,
    ) -> Asset:
        return Asset(
            symbol="MC.PA",
            name="LVMH",
            exchange="Paris",
            currency="EUR",
        )


class FakeMarketDataProvider:
    def search_assets(self, query: str) -> list[Asset]:
        return []

    def get_daily_prices(
        self,
        asset: Asset,
        start_date: date,
        end_date: date,
    ) -> list[DailyPriceObservation]:
        return [
            DailyPriceObservation(
                asset=asset,
                date=date(2020, 3, 13),
                open=Decimal("310.00"),
                high=Decimal("320.00"),
                low=Decimal("300.00"),
                close=Decimal("314.90"),
                adjusted_close=Decimal("280.99"),
                volume=1_100_000,
            ),
            DailyPriceObservation(
                asset=asset,
                date=date(2020, 3, 16),
                open=Decimal("300.00"),
                high=Decimal("310.00"),
                low=Decimal("290.00"),
                close=Decimal("297.60"),
                adjusted_close=Decimal("265.56"),
                volume=1_000_000,
            ),
        ]


class EmptyMarketDataProvider(FakeMarketDataProvider):
    def get_daily_prices(
        self,
        asset: Asset,
        start_date: date,
        end_date: date,
    ) -> list[DailyPriceObservation]:
        return []


def test_get_price_series_resolves_asset_and_extracts_series() -> None:
    service = MarketSeriesService(
        provider=FakeMarketDataProvider(),
        asset_resolver=FakeAssetResolver(),
    )

    result = service.get_price_series(
        asset_query="LVMH",
        start_date=date(2020, 3, 13),
        end_date=date(2020, 3, 16),
        preferred_exchange="Paris",
        preferred_currency="EUR",
    )

    assert result.identifier == "MC.PA"
    assert result.kind == SeriesKind.PRICE
    assert result.unit == "EUR"
    assert result.observation_count == 2
    assert result.metadata["field"] == "adjusted_close"


def test_get_price_series_for_identified_asset() -> None:
    service = MarketSeriesService(
        provider=FakeMarketDataProvider(),
        asset_resolver=FakeAssetResolver(),
    )

    asset = Asset(
        symbol="MC.PA",
        name="LVMH",
        currency="EUR",
    )

    result = service.get_price_series_for_asset(
        asset=asset,
        start_date=date(2020, 3, 13),
        end_date=date(2020, 3, 16),
        use_adjusted_close=False,
    )

    assert result.values.iloc[0] == pytest.approx(314.90)
    assert result.metadata["field"] == "close"


def test_get_price_series_rejects_invalid_period() -> None:
    service = MarketSeriesService(
        provider=FakeMarketDataProvider(),
        asset_resolver=FakeAssetResolver(),
    )

    with pytest.raises(ValueError, match="start_date"):
        service.get_price_series(
            asset_query="LVMH",
            start_date=date(2020, 3, 16),
            end_date=date(2020, 3, 13),
        )


def test_get_price_series_rejects_empty_data() -> None:
    service = MarketSeriesService(
        provider=EmptyMarketDataProvider(),
        asset_resolver=FakeAssetResolver(),
    )

    with pytest.raises(
        ValueError,
        match="No price observations",
    ):
        service.get_price_series(
            asset_query="LVMH",
            start_date=date(2020, 3, 13),
            end_date=date(2020, 3, 16),
        )
