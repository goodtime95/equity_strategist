from datetime import date
from decimal import Decimal

from equity_strategist.domain.models import Asset, PriceOnDateResult
from equity_strategist.services.market_queries import MarketQueryService


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


class FakePriceTool:
    def get_price_on_date(
        self,
        asset: Asset,
        target_date: date,
        use_adjusted_close: bool = True,
    ) -> PriceOnDateResult:
        return PriceOnDateResult(
            asset=asset,
            requested_date=target_date,
            effective_date=date(2020, 3, 13),
            price=Decimal("280.99"),
            price_type="adjusted_close",
            used_previous_session=True,
        )


def test_get_price_on_date() -> None:
    service = MarketQueryService(
        asset_resolver=FakeAssetResolver(),
        price_tool=FakePriceTool(),
    )

    result = service.get_price_on_date(
        asset_query="LVMH",
        target_date=date(2020, 3, 15),
        preferred_exchange="Paris",
        preferred_currency="EUR",
    )

    assert result.asset.symbol == "MC.PA"
    assert result.requested_date == date(2020, 3, 15)
    assert result.effective_date == date(2020, 3, 13)
    assert result.price == Decimal("280.99")
    assert result.used_previous_session is True
