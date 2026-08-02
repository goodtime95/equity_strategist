from datetime import date

from equity_strategist.app import build_market_query_service


def main() -> None:
    service = build_market_query_service()

    result = service.get_price_on_date(
        asset_query="LVMH",
        target_date=date(2020, 3, 15),
        preferred_exchange="Paris",
        preferred_currency="EUR",
    )

    print(f"Actif : {result.asset.name}")
    print(f"Ticker : {result.asset.symbol}")
    print(f"Date demandée : {result.requested_date}")
    print(f"Date utilisée : {result.effective_date}")
    print(f"Prix : {result.price}")
    print(f"Type de prix : {result.price_type}")
    print(f"Séance précédente utilisée : {result.used_previous_session}")


if __name__ == "__main__":
    main()
