from datetime import date, timedelta

from equity_strategist.data_providers.base import MarketDataProvider
from equity_strategist.domain.asset import Asset
from equity_strategist.domain.results import PriceOnDateResult


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
        use_adjusted_close: bool = True,
    ) -> PriceOnDateResult:
        """Return the price on a date or the previous available session."""
        lookback_start = target_date - timedelta(days=10)

        prices = self.provider.get_daily_prices(
            asset=asset,
            start_date=lookback_start,
            end_date=target_date,
        )

        if not prices:
            raise ValueError(
                f"No market data available for {asset.symbol} "
                f"on or before {target_date}"
            )

        selected_price = prices[-1]

        if use_adjusted_close and selected_price.adjusted_close is not None:
            price = selected_price.adjusted_close
            price_type = "adjusted_close"
        else:
            price = selected_price.close
            price_type = "close"

        return PriceOnDateResult(
            asset=asset,
            requested_date=target_date,
            effective_date=selected_price.date,
            price=price,
            price_type=price_type,
            used_previous_session=selected_price.date != target_date,
        )
