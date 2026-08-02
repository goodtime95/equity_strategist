from datetime import date

from equity_strategist.data_providers.yahoo import (
    YahooFinanceProvider,
)
from equity_strategist.domain.models import Asset
from equity_strategist.tools.prices import PriceTool


def main() -> None:
    provider = YahooFinanceProvider()
    tool = PriceTool(provider)

    lvmh = Asset(
        symbol="MC.PA",
        name="LVMH",
        exchange="Paris",
        currency="EUR",
    )

    result = tool.get_price_on_date(
        asset=lvmh,
        target_date=date(2020, 3, 15),
    )

    print(f"Actif : {result.asset.name}")
    print(f"Date demandée : {result.requested_date}")
    print(f"Date utilisée : {result.effective_date}")
    print(f"Prix : {result.price}")
    print(f"Type : {result.price_type}")
    print(f"Séance précédente utilisée : {result.used_previous_session}")


if __name__ == "__main__":
    main()
