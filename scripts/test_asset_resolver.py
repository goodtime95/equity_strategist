from equity_strategist.data_providers.yahoo import (
    YahooFinanceProvider,
)
from equity_strategist.tools.assets import AssetResolver


def main() -> None:
    provider = YahooFinanceProvider()
    resolver = AssetResolver(provider)

    asset = resolver.resolve(
        query="LVMH",
        preferred_exchange="Paris",
        preferred_currency="EUR",
    )

    print(f"Ticker : {asset.symbol}")
    print(f"Nom : {asset.name}")
    print(f"Place : {asset.exchange}")
    print(f"Devise : {asset.currency}")


if __name__ == "__main__":
    main()
