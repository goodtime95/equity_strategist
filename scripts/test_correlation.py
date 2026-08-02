from datetime import date

from equity_strategist.compute.correlation import (
    compute_correlation,
    compute_rolling_correlation,
)
from equity_strategist.compute.returns import (
    ReturnMethod,
    compute_returns,
)
from equity_strategist.data_providers.yahoo import (
    YahooFinanceProvider,
)
from equity_strategist.domain.asset import Asset
from equity_strategist.extractors.price_series import (
    extract_price_series,
)


def build_returns(
    provider: YahooFinanceProvider,
    asset: Asset,
):
    prices = provider.get_daily_prices(
        asset=asset,
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
    )

    price_series = extract_price_series(
        asset=asset,
        prices=prices,
        use_adjusted_close=True,
    )

    return compute_returns(
        price_series=price_series,
        method=ReturnMethod.LOG,
    )


def main() -> None:
    provider = YahooFinanceProvider()

    lvmh = Asset(
        symbol="MC.PA",
        name="LVMH",
        exchange="Paris",
        currency="EUR",
    )

    hermes = Asset(
        symbol="RMS.PA",
        name="Hermès",
        exchange="Paris",
        currency="EUR",
    )

    lvmh_returns = build_returns(provider, lvmh)
    hermes_returns = build_returns(provider, hermes)

    correlation = compute_correlation(
        first_series=lvmh_returns,
        second_series=hermes_returns,
    )

    rolling = compute_rolling_correlation(
        first_series=lvmh_returns,
        second_series=hermes_returns,
        window=60,
    )

    print(f"Corrélation totale : {correlation:.3f}")
    print()
    print("Dernières corrélations glissantes 60 jours :")
    print(rolling.values.tail())


if __name__ == "__main__":
    main()
