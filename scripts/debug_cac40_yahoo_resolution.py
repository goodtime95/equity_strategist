from equity_strategist.data_providers.yahoo import (
    YahooFinanceProvider,
)

FAILED_NAMES = (
    "ARCELORMITTAL SA",
    "KERING",
    "ORANGE",
    "SAINT GOBAIN",
    "SANOFI",
    "VINCI",
)


def main() -> None:
    provider = YahooFinanceProvider()

    for name in FAILED_NAMES:
        print()
        print("=" * 80)
        print(name)
        print("=" * 80)

        candidates = provider.search_assets(name)

        if not candidates:
            print("NO CANDIDATES")
            continue

        for candidate in candidates:
            print(
                f"symbol={candidate.symbol:<12} "
                f"exchange={str(candidate.exchange):<20} "
                f"currency={str(candidate.currency):<6} "
                f"name={candidate.name}"
            )


if __name__ == "__main__":
    main()
