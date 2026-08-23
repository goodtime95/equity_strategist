from pprint import pprint

import yfinance as yf

SYMBOLS = (
    "SU.PA",
    "SUN.MX",
    "US80687P1066.SG",
    "SAF.PA",
    "SAFRY",
    "SIE.DE",
    "SIEGY",
    "TTE",
    "TTE.PA",
)


FIELDS = (
    "symbol",
    "shortName",
    "longName",
    "quoteType",
    "exchange",
    "fullExchangeName",
    "market",
    "currency",
    "financialCurrency",
    "country",
    "industry",
    "sector",
    "underlyingSymbol",
)


def main() -> None:
    for symbol in SYMBOLS:
        print()
        print("=" * 100)
        print(f"SYMBOL: {symbol}")
        print("=" * 100)

        ticker = yf.Ticker(symbol)

        try:
            info = ticker.get_info()
        except Exception as exc:
            print(f"ERROR: {exc}")
            continue

        selected = {
            field: info.get(field) for field in FIELDS if info.get(field) is not None
        }

        pprint(selected)


if __name__ == "__main__":
    main()
