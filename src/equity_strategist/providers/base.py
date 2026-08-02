from datetime import date
from typing import Protocol

from equity_strategist.domain.models import Asset, PriceBar


class MarketDataProvider(Protocol):
    """Contract implemented by every external market-data provider."""

    def search_assets(self, query: str) -> list[Asset]:
        """Find assets matching a company name or ticker."""
        ...

    def get_daily_prices(
        self,
        asset: Asset,
        start_date: date,
        end_date: date,
    ) -> list[PriceBar]:
        """Return daily market data over the requested period."""
        ...
