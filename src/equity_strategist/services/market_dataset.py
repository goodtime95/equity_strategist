from datetime import date

from equity_strategist.domain.asset import Asset
from equity_strategist.domain.market_dataset import MarketDataset
from equity_strategist.services.market_series import MarketSeriesService


class MarketDatasetService:
    """Build collections of normalized market series."""

    def __init__(
        self,
        market_series_service: MarketSeriesService,
    ) -> None:
        self.market_series_service = market_series_service

    def build_price_dataset(
        self,
        asset_queries: list[str],
        start_date: date,
        end_date: date,
        universe: str | None = None,
        use_adjusted_close: bool = True,
    ) -> MarketDataset:
        """Build a price dataset for several assets."""
        if not asset_queries:
            raise ValueError("at least one asset is required")

        series_by_symbol = {}

        for asset_query in asset_queries:
            series = self.market_series_service.get_price_series(
                asset_query=asset_query,
                start_date=start_date,
                end_date=end_date,
                use_adjusted_close=use_adjusted_close,
            )

            if series.identifier in series_by_symbol:
                raise ValueError(f"duplicate asset resolved to {series.identifier}")

            series_by_symbol[series.identifier] = series

        return MarketDataset(
            series_by_symbol=series_by_symbol,
            universe=universe,
        )

    def build_price_dataset_for_assets(
        self,
        assets: tuple[Asset, ...],
        start_date: date,
        end_date: date,
        universe: str | None = None,
        adjusted_close: bool = True,
    ) -> MarketDataset:
        """Build a price dataset from already resolved assets."""

        if not assets:
            raise ValueError("at least one asset is required")

        series_by_symbol = {}

        for asset in assets:
            price_series = self.market_series_service.get_price_series_for_asset(
                asset=asset,
                start_date=start_date,
                end_date=end_date,
                adjusted_close=adjusted_close,
            )

            if price_series.identifier in series_by_symbol:
                raise ValueError(
                    f"duplicate asset resolved to {price_series.identifier}"
                )

            series_by_symbol[price_series.identifier] = price_series

        return MarketDataset(
            series_by_symbol=series_by_symbol,
            universe=universe,
        )
