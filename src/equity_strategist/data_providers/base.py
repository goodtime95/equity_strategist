from datetime import date
from typing import Protocol

from equity_strategist.domain.asset import Asset
from equity_strategist.domain.observations import (
    DailyPriceObservation,
)


class AssetSearchProvider(Protocol):
    """Contract for external asset discovery and listing resolution."""

    def search_assets(
        self,
        query: str,
    ) -> list[Asset]:
        """Find assets matching a company name or ticker."""
        ...

    def select_primary_asset(
        self,
        assets: list[Asset],
    ) -> Asset | None:
        """Return a primary listing when it can be identified reliably."""
        ...


class MarketDataProvider(Protocol):
    """Contract for external market-data retrieval."""

    def get_daily_prices(
        self,
        asset: Asset,
        start_date: date,
        end_date: date,
    ) -> list[DailyPriceObservation]:
        """Return daily market observations over a date interval."""
        ...
