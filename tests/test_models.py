from datetime import date
from decimal import Decimal

from equity_strategist.domain.models import Asset, PriceBar


def test_asset_creation() -> None:
    asset = Asset(
        symbol="MC.PAR",
        name="LVMH",
        exchange="Euronext Paris",
        currency="EUR",
    )

    assert asset.symbol == "MC.PAR"
    assert asset.currency == "EUR"


def test_price_bar_creation() -> None:
    asset = Asset(symbol="MC.PAR", name="LVMH")

    price = PriceBar(
        asset=asset,
        date=date(2020, 3, 16),
        open=Decimal("315.00"),
        high=Decimal("325.00"),
        low=Decimal("300.00"),
        close=Decimal("310.00"),
        volume=1_000_000,
    )

    assert price.asset == asset
    assert price.close == Decimal("310.00")
    assert price.date == date(2020, 3, 16)
