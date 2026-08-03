from datetime import date

from equity_strategist.app import build_market_series_service
from equity_strategist.domain.asset import Asset


def main() -> None:
    service = build_market_series_service()

    lvmh = Asset(
        symbol="MC.PA",
        name="LVMH",
        exchange="Paris",
        currency="EUR",
    )

    series = service.get_price_series_for_asset(
        asset=lvmh,
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
        use_adjusted_close=True,
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
