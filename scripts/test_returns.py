from datetime import date

from equity_strategist.compute.returns import (
    ReturnMethod,
    compute_returns,
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
        start_date=date(2020, 3, 10),
        end_date=date(2020, 3, 20),
    )

    price_series = build_price_series(
        asset=asset,
        prices=prices,
        use_adjusted_close=True,
    )

    return_series = compute_returns(
        price_series,
        method=ReturnMethod.SIMPLE,
    )

    print(return_series.values)
    print()
    print(f"Observations : {return_series.observation_count}")
    print(f"Méthode : {return_series.metadata['return_method']}")


if __name__ == "__main__":
    main()
