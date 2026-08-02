from datetime import date
from decimal import Decimal

import pandas as pd

from equity_strategist.data_providers.yahoo import YahooFinanceProvider
from equity_strategist.domain.asset import Asset


def test_quote_to_asset() -> None:
    quote = {
        "symbol": "MC.PA",
        "longname": "LVMH Moët Hennessy - Louis Vuitton",
        "exchange": "PAR",
        "exchDisp": "Paris",
        "currency": "EUR",
        "quoteType": "EQUITY",
    }

    asset = YahooFinanceProvider._quote_to_asset(quote)

    assert asset is not None
    assert asset.symbol == "MC.PA"
    assert asset.currency == "EUR"
    assert asset.exchange == "Paris"


def test_quote_without_symbol_is_ignored() -> None:
    asset = YahooFinanceProvider._quote_to_asset(
        {
            "quoteType": "EQUITY",
            "longname": "Unknown company",
        }
    )

    assert asset is None


def test_row_to_daily_price_observation() -> None:
    asset = Asset(symbol="MC.PA", name="LVMH")

    row = pd.Series(
        {
            "Open": 315.0,
            "High": 325.0,
            "Low": 300.0,
            "Close": 310.0,
            "Adj Close": 298.5,
            "Volume": 1_000_000,
        }
    )

    timestamp = pd.Timestamp(
        "2020-03-16",
        tz="Europe/Paris",
    )

    price = YahooFinanceProvider._row_to_observation(
        asset,
        timestamp,
        row,
    )

    assert price.date == date(2020, 3, 16)
    assert price.close == Decimal("310.0")
    assert price.adjusted_close == Decimal("298.5")
    assert price.volume == 1_000_000


def test_start_date_must_precede_end_date() -> None:
    provider = YahooFinanceProvider()
    asset = Asset(symbol="MC.PA")

    try:
        provider.get_daily_prices(
            asset=asset,
            start_date=date(2020, 3, 17),
            end_date=date(2020, 3, 15),
        )
    except ValueError as exc:
        assert str(exc) == ("start_date must be before or equal to end_date")
    else:
        raise AssertionError("ValueError was not raised")
