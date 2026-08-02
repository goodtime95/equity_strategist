from datetime import date

from equity_strategist.compute.returns import (
    ReturnMethod,
    compute_returns,
)
from equity_strategist.compute.volatility import (
    compute_rolling_volatility,
    compute_volatility,
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
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
    )

    price_series = build_price_series(
        asset=asset,
        prices=prices,
        use_adjusted_close=True,
    )

    return_series = compute_returns(
        price_series=price_series,
        method=ReturnMethod.LOG,
    )

    volatility = compute_volatility(
        return_series=return_series,
        annualization_factor=252,
    )

    rolling_volatility = compute_rolling_volatility(
        return_series=return_series,
        window=20,
        annualization_factor=252,
    )

    print(f"Volatilité annualisée : {volatility:.2%}")
    print()
    print("Dernières volatilités glissantes 20 jours :")
    print(rolling_volatility.values.tail())


if __name__ == "__main__":
    main()
