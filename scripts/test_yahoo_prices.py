from datetime import date

from equity_strategist.data_providers.yahoo import YahooFinanceProvider
from equity_strategist.domain.asset import Asset


def main() -> None:
    provider = YahooFinanceProvider()
    lvmh = Asset(
        symbol="MC.PA",
        name="LVMH",
        exchange="Paris",
        currency="EUR",
    )

    prices = provider.get_daily_prices(
        asset=lvmh,
        start_date=date(2020, 3, 13),
        end_date=date(2020, 3, 17),
    )

    for price in prices:
        print(
            f"{price.date} | "
            f"close={price.close} | "
            f"adjusted_close={price.adjusted_close}"
        )


if __name__ == "__main__":
    main()
