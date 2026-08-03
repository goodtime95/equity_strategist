from datetime import date

from equity_strategist.compute.drawdown import (
    compute_maximum_drawdown,
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

    observations = provider.get_daily_prices(
        asset=asset,
        start_date=date(2020, 1, 1),
        end_date=date(2025, 12, 31),
    )

    price_series = extract_price_series(
        asset=asset,
        observations=observations,
        use_adjusted_close=True,
    )

    result = compute_maximum_drawdown(price_series)

    print(f"Maximum drawdown : {result.maximum_drawdown:.2%}")
    print(f"Peak date : {result.peak_date.date()}")
    print(f"Trough date : {result.trough_date.date()}")

    if result.recovery_date is None:
        print("Recovery date : not recovered")
    else:
        print(f"Recovery date : {result.recovery_date.date()}")


if __name__ == "__main__":
    main()
