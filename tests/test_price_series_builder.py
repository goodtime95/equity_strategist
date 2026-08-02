from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from equity_strategist.domain.market_series import SeriesKind
from equity_strategist.domain.models import Asset, PriceBar
from equity_strategist.series_builders.prices import build_price_series


def test_build_adjusted_price_series() -> None:
    asset = Asset(
        symbol="MC.PA",
        name="LVMH",
        currency="EUR",
    )

    prices = [
        PriceBar(
            asset=asset,
            date=date(2020, 3, 16),
            open=Decimal("300.00"),
            high=Decimal("310.00"),
            low=Decimal("290.00"),
            close=Decimal("297.60"),
            adjusted_close=Decimal("265.56"),
            volume=1_000_000,
        ),
        PriceBar(
            asset=asset,
            date=date(2020, 3, 13),
            open=Decimal("310.00"),
            high=Decimal("320.00"),
            low=Decimal("300.00"),
            close=Decimal("314.90"),
            adjusted_close=Decimal("280.99"),
            volume=1_100_000,
        ),
    ]

    series = build_price_series(
        asset=asset,
        prices=prices,
        use_adjusted_close=True,
    )

    assert series.identifier == "MC.PA"
    assert series.kind == SeriesKind.PRICE
    assert series.unit == "EUR"
    assert series.metadata["field"] == "adjusted_close"
    assert series.start_date == pd.Timestamp("2020-03-13")
    assert series.values.iloc[0] == pytest.approx(280.99)


def test_build_price_series_rejects_another_asset() -> None:
    lvmh = Asset(symbol="MC.PA", name="LVMH", currency="EUR")
    hermes = Asset(symbol="RMS.PA", name="Hermès", currency="EUR")

    prices = [
        PriceBar(
            asset=hermes,
            date=date(2020, 3, 13),
            open=Decimal("600.00"),
            high=Decimal("610.00"),
            low=Decimal("590.00"),
            close=Decimal("605.00"),
            adjusted_close=Decimal("600.00"),
            volume=100_000,
        )
    ]

    with pytest.raises(ValueError, match="requested asset"):
        build_price_series(
            asset=lvmh,
            prices=prices,
        )
