from equity_strategist.asset_registry import (
    build_default_asset_registry,
)
from equity_strategist.data_providers.yahoo import (
    YahooFinanceProvider,
)
from equity_strategist.tools.assets import AssetResolver
from equity_strategist.tools.universe_assets import (
    UniverseAssetResolver,
)
from equity_strategist.universe_providers.euronext import (
    EuronextUniverseProvider,
)


def main() -> None:
    universe_provider = EuronextUniverseProvider()

    constituents = universe_provider.get_constituents("FR0003500008-XPAR")

    resolver = UniverseAssetResolver(
        asset_resolver=AssetResolver(build_default_asset_registry()),
        market_data_provider=YahooFinanceProvider(),
    )

    resolved = []
    failed = []

    for constituent in constituents:
        try:
            asset = resolver.resolve(constituent)

            resolved.append(
                (
                    constituent,
                    asset,
                )
            )

        except Exception as exc:
            failed.append(
                (
                    constituent,
                    exc,
                )
            )

    print("=" * 70)
    print("RESOLVED")
    print("=" * 70)

    for constituent, asset in resolved:
        print(f"{constituent.name:<25} -> {asset.symbol:<12} {asset.name}")

    print()

    print("=" * 70)
    print("FAILED")
    print("=" * 70)

    for constituent, exc in failed:
        print(f"{constituent.name:<25} -> {type(exc).__name__}: {exc}")

    print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(f"Constituents : {len(constituents)}")
    print(f"Resolved     : {len(resolved)}")
    print(f"Failed       : {len(failed)}")


if __name__ == "__main__":
    main()
