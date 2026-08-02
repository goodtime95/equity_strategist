from equity_strategist.providers.yahoo import YahooFinanceProvider


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
