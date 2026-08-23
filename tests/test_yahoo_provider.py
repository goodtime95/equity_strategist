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


def test_primary_listing_score_prefers_home_market() -> None:
    score = YahooFinanceProvider._primary_listing_score(
        country="France",
        market="fr_market",
    )

    assert score == 100


def test_primary_listing_score_penalizes_foreign_us_listing() -> None:
    score = YahooFinanceProvider._primary_listing_score(
        country="France",
        market="us_market",
    )

    assert score == -30


def test_primary_listing_score_penalizes_depositary_receipt_market() -> None:
    score = YahooFinanceProvider._primary_listing_score(
        country=None,
        market="dr_market",
    )

    assert score == -50


def test_primary_listing_score_accepts_us_company_on_us_market() -> None:
    score = YahooFinanceProvider._primary_listing_score(
        country="United States",
        market="us_market",
    )

    assert score == 100


def test_select_primary_asset_prefers_home_listing(
    monkeypatch,
) -> None:
    assets = [
        Asset(
            symbol="TTE",
            name="TotalEnergies SE",
        ),
        Asset(
            symbol="TTE.PA",
            name="TotalEnergies SE",
        ),
    ]

    infos = {
        "TTE": {
            "country": "France",
            "market": "us_market",
        },
        "TTE.PA": {
            "country": "France",
            "market": "fr_market",
        },
    }

    class FakeTicker:
        def __init__(
            self,
            symbol: str,
        ) -> None:
            self.symbol = symbol

        def get_info(self):
            return infos[self.symbol]

    monkeypatch.setattr(
        "equity_strategist.data_providers.yahoo.yf.Ticker",
        FakeTicker,
    )

    provider = YahooFinanceProvider()

    primary_asset = provider.select_primary_asset(assets)

    assert primary_asset is not None
    assert primary_asset.symbol == "TTE.PA"


def test_select_primary_asset_returns_none_when_no_candidate_dominates(
    monkeypatch,
) -> None:
    assets = [
        Asset(
            symbol="ABC.PA",
            name="ABC",
        ),
        Asset(
            symbol="ABC.L",
            name="ABC",
        ),
    ]

    infos = {
        "ABC.PA": {
            "country": None,
            "market": None,
        },
        "ABC.L": {
            "country": None,
            "market": None,
        },
    }

    class FakeTicker:
        def __init__(
            self,
            symbol: str,
        ) -> None:
            self.symbol = symbol

        def get_info(self):
            return infos[self.symbol]

    monkeypatch.setattr(
        "equity_strategist.data_providers.yahoo.yf.Ticker",
        FakeTicker,
    )

    provider = YahooFinanceProvider()

    primary_asset = provider.select_primary_asset(assets)

    assert primary_asset is None
