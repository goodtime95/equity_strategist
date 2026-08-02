from datetime import date

from equity_strategist.compute.performance import (
    compute_annualized_performance,
    compute_total_performance,
)
from equity_strategist.data_providers.yahoo import (
    YahooFinanceProvider,
)
from equity_strategist.domain.models import Asset
from equity_strategist.series_builders.prices import (
    build_price_series,
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

    price_series = build_price_series(
        asset=asset,
        prices=prices,
        use_adjusted_close=True,
    )

    total_performance = compute_total_performance(
        price_series
    )

    annualized_performance = (
        compute_annualized_performance(price_series)
    )

    print(
        "Performance totale : "
        f"{total_performance:.2%}"
    )
    print(
        "Performance annualisée : "
        f"{annualized_performance:.2%}"
    )


if __name__ == "__main__":
    main()
