from datetime import date

from equity_strategist.data_providers.base import MarketDataProvider
from equity_strategist.domain.models import Asset, PriceBar


class PriceTool:
    """High-level price queries."""

    def __init__(
        self,
        provider: MarketDataProvider,
    ) -> None:
        self.provider = provider

    def get_price_on_date(
        self,
        asset: Asset,
        target_date: date,
    ) -> PriceBar:
        raise NotImplementedError
