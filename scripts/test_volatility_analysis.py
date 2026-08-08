from datetime import date

from equity_strategist.app import (
    build_volatility_analysis_service,
)


def main() -> None:
    service = build_volatility_analysis_service()

    result = service.compare(
        asset_queries=[
            "LVMH",
            "Hermès",
            "ASML",
        ],
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
    )

    print(
        f"Period: {result.start_date} -> "
        f"{result.end_date}"
    )
    print()

    for rank, item in enumerate(
        result.items,
        start=1,
    ):
        print(
            f"{rank}. {item.name} "
            f"({item.symbol}) : "
            f"{item.volatility:.2%}"
        )


if __name__ == "__main__":
    main()
