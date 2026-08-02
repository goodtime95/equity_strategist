from datetime import date
from typing import Protocol

from equity_strategist.domain.asset import Asset
from equity_strategist.domain.observations import (
    DailyPriceObservation,
)


class MarketDataProvider(Protocol):
    """Contract implemented by external market-data providers."""

    def search_assets(self, query: str) -> list[Asset]:
        """Find assets matching a company name or ticker."""
        ...

    def get_daily_prices(
        self,
        asset: Asset,
        start_date: date,
        end_date: date,
    ) -> list[DailyPriceObservation]:
        """Return daily market observations over a date interval."""
        ...
