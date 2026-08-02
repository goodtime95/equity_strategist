from datetime import date

from equity_strategist.compute.performance import (
    compute_annualized_performance,
    compute_total_performance,
)
from equity_strategist.data_providers.yahoo import (
    YahooFinanceProvider,
)
from equity_strategist.domain.asset import Asset
from equity_strategist.extractors.price_series import (
    extract_price_series,
)


def main() -> None:
    provider = YahooFinanceProvider()

    asset = Asset(
        symbol="MC.PA",
        name="LVMH",
        exchange="Paris",
        currency="EUR",
    )

    prices = provider.get_daily_prices(
        asset=asset,
        start_date=date(2020, 1, 1),
        end_date=date(2025, 12, 31),
    )

    price_series = extract_price_series(
        asset=asset,
        prices=prices,
        use_adjusted_close=True,
    )

    total_performance = compute_total_performance(price_series)

    annualized_performance = compute_annualized_performance(price_series)

    print(f"Performance totale : {total_performance:.2%}")
    print(f"Performance annualisée : {annualized_performance:.2%}")


if __name__ == "__main__":
    main()
