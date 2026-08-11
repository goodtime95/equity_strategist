from equity_strategist.universe_providers.euronext import (
    EuronextUniverseProvider,
)


def main() -> None:
    provider = EuronextUniverseProvider()

    constituents = provider.get_constituents("FR0003500008-XPAR")

    print(f"Number of constituents: {len(constituents)}")
    print()

    for constituent in constituents:
        print(f"{constituent.name} | {constituent.isin} | {constituent.exchange}")


if __name__ == "__main__":
    main()
