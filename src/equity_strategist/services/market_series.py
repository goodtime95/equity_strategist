from datetime import date

from equity_strategist.data_providers.base import MarketDataProvider
from equity_strategist.domain.asset import Asset
from equity_strategist.domain.market_series import MarketSeries
from equity_strategist.extractors.price_series import extract_price_series
from equity_strategist.tools.assets import AssetResolver


class MarketSeriesService:
    """Retrieve and normalize market time series."""

    def __init__(
        self,
        provider: MarketDataProvider,
        asset_resolver: AssetResolver,
    ) -> None:
        self.provider = provider
        self.asset_resolver = asset_resolver

    def get_price_series(
        self,
        asset_query: str,
        start_date: date,
        end_date: date,
        preferred_exchange: str | None = None,
        preferred_currency: str | None = None,
        use_adjusted_close: bool = True,
    ) -> MarketSeries:
        """Resolve an asset and return a normalized price series."""
        if start_date > end_date:
            raise ValueError("start_date must be before or equal to end_date")

        asset = self.asset_resolver.resolve(
            query=asset_query,
            preferred_exchange=preferred_exchange,
            preferred_currency=preferred_currency,
        )

        return self.get_price_series_for_asset(
            asset=asset,
            start_date=start_date,
            end_date=end_date,
            use_adjusted_close=use_adjusted_close,
        )

    def get_price_series_for_asset(
        self,
        asset: Asset,
        start_date: date,
        end_date: date,
        use_adjusted_close: bool = True,
    ) -> MarketSeries:
        """Return a normalized price series for an identified asset."""
        if start_date > end_date:
            raise ValueError("start_date must be before or equal to end_date")

        observations = self.provider.get_daily_prices(
            asset=asset,
            start_date=start_date,
            end_date=end_date,
        )

        if not observations:
            raise ValueError(
                f"No price observations available for {asset.symbol} "
                f"between {start_date} and {end_date}"
            )

        return extract_price_series(
            asset=asset,
            observations=observations,
            use_adjusted_close=use_adjusted_close,
        )
