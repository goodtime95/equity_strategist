from equity_strategist.data_providers.yahoo import YahooFinanceProvider


def main() -> None:
    provider = YahooFinanceProvider()

    assets = provider.search_assets("LVMH")

    for asset in assets:
        print(f"{asset.symbol} | {asset.name} | {asset.exchange} | {asset.currency}")


if __name__ == "__main__":
    main()
