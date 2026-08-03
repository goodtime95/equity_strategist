from datetime import date

from equity_strategist.app import build_market_series_service


def main() -> None:
    service = build_market_series_service()

    series = service.get_price_series(
        asset_query="LVMH",
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
        preferred_exchange="Paris",
        preferred_currency="EUR",
    )

    print(f"Identifier : {series.identifier}")
    print(f"Kind : {series.kind}")
    print(f"Unit : {series.unit}")
    print(f"Start : {series.start_date.date()}")
    print(f"End : {series.end_date.date()}")
    print(f"Observations : {series.observation_count}")
    print()
    print(series.values.tail())


if __name__ == "__main__":
    main()
