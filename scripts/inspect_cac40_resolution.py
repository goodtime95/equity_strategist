from equity_strategist.app import (
    build_equity_strategist,
)


def main() -> None:
    strategist = build_equity_strategist()

    executor = strategist.executor

    constituents = executor.universe_constituent_service.get_constituents("CAC 40")

    print(f"CAC 40 constituents: {len(constituents)}")

    for constituent in constituents:
        print()
        print("=" * 100)
        print(f"NAME: {constituent.name}")
        print(f"ISIN: {constituent.isin}")
        print(f"PROVIDER SYMBOL: {constituent.provider_symbol}")
        print(f"EXCHANGE: {constituent.exchange}")

        try:
            asset = executor.universe_asset_resolver.resolve(constituent)

        except Exception as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}")
            continue

        print(f"RESOLVED: {asset.symbol} | {asset.name} | {asset.exchange}")


if __name__ == "__main__":
    main()
