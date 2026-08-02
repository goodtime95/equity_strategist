from datetime import date
from decimal import Decimal

from equity_strategist.domain.asset import Asset
from equity_strategist.domain.observations import DailyPriceObservation
from equity_strategist.tools.prices import PriceTool


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
                open=Decimal("320.00"),
                high=Decimal("325.00"),
                low=Decimal("300.00"),
                close=Decimal("314.90"),
                adjusted_close=Decimal("280.99"),
                volume=1_000_000,
            )
        ]


def test_get_price_uses_previous_market_session() -> None:
    provider = FakeMarketDataProvider()
    tool = PriceTool(provider)

    asset = Asset(
        symbol="MC.PA",
        name="LVMH",
        currency="EUR",
    )

    result = tool.get_price_on_date(
        asset=asset,
        target_date=date(2020, 3, 15),
    )

    assert result.requested_date == date(2020, 3, 15)
    assert result.effective_date == date(2020, 3, 13)
    assert result.price == Decimal("280.99")
    assert result.price_type == "adjusted_close"
    assert result.used_previous_session is True
