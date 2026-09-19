from datetime import date, timedelta

from equity_strategist.domain.asset import Asset
from equity_strategist.domain.errors import InsufficientDataError
from equity_strategist.domain.market_dataset import (
    AlignedMarketDataset,
    MarketDataset,
    MarketDatasetBundle,
)
from equity_strategist.domain.market_series import MarketSeries
from equity_strategist.services.market_series import MarketSeriesService


class MarketDatasetService:
    """Build collections of normalized market series."""

    PREVIOUS_SESSION_LOOKBACK_DAYS = 10

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
        use_adjusted_close: bool = True,
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
                use_adjusted_close=use_adjusted_close,
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

    def build_price_dataset_bundle(
        self,
        asset_queries: list[str],
        start_date: date,
        end_date: date,
        benchmark_query: str | None = None,
        universe: str | None = None,
    ) -> MarketDatasetBundle:
        """Build one runtime dataset and retain asset/benchmark roles."""
        if not asset_queries:
            raise ValueError("at least one asset is required")

        series_by_symbol: dict[str, MarketSeries] = {}
        asset_symbols: list[str] = []

        for query in asset_queries:
            series = self.market_series_service.get_price_series(
                asset_query=query,
                start_date=start_date,
                end_date=end_date,
            )
            self._add_unique_series(series_by_symbol, series)
            asset_symbols.append(series.identifier)

        benchmark_symbol = None

        if benchmark_query is not None:
            benchmark_series = self.market_series_service.get_price_series(
                asset_query=benchmark_query,
                start_date=start_date,
                end_date=end_date,
                existing_series=series_by_symbol,
            )
            series_by_symbol.setdefault(benchmark_series.identifier, benchmark_series)
            benchmark_symbol = benchmark_series.identifier

        return MarketDatasetBundle(
            dataset=MarketDataset(
                series_by_symbol=series_by_symbol,
                universe=universe,
            ),
            asset_symbols=tuple(asset_symbols),
            benchmark_symbol=benchmark_symbol,
        )

    def build_price_dataset_bundle_for_assets(
        self,
        assets: tuple[Asset, ...],
        start_date: date,
        end_date: date,
        benchmark_query: str | None = None,
        universe: str | None = None,
    ) -> MarketDatasetBundle:
        """Build a role-aware dataset from resolved universe assets."""
        if not assets:
            raise ValueError("at least one asset is required")

        series_by_symbol: dict[str, MarketSeries] = {}
        asset_symbols: list[str] = []

        for asset in assets:
            series = self.market_series_service.get_price_series_for_asset(
                asset=asset,
                start_date=start_date,
                end_date=end_date,
            )
            self._add_unique_series(series_by_symbol, series)
            asset_symbols.append(series.identifier)

        benchmark_symbol = None

        if benchmark_query is not None:
            benchmark_series = self.market_series_service.get_price_series(
                asset_query=benchmark_query,
                start_date=start_date,
                end_date=end_date,
                existing_series=series_by_symbol,
            )
            series_by_symbol.setdefault(benchmark_series.identifier, benchmark_series)
            benchmark_symbol = benchmark_series.identifier

        return MarketDatasetBundle(
            dataset=MarketDataset(
                series_by_symbol=series_by_symbol,
                universe=universe,
            ),
            asset_symbols=tuple(asset_symbols),
            benchmark_symbol=benchmark_symbol,
        )

    def build_aligned_price_dataset(
        self,
        asset_queries: list[str],
        requested_start_date: date,
        requested_end_date: date,
        benchmark_query: str | None = None,
        universe: str | None = None,
    ) -> AlignedMarketDataset:
        """Fetch and align assets on common previous-session endpoints."""
        bundle = self.build_price_dataset_bundle(
            asset_queries=asset_queries,
            start_date=self.history_fetch_start(requested_start_date),
            end_date=requested_end_date,
            benchmark_query=benchmark_query,
            universe=universe,
        )
        return self.align_price_dataset(
            bundle=bundle,
            requested_start_date=requested_start_date,
            requested_end_date=requested_end_date,
        )

    @staticmethod
    def align_price_dataset(
        bundle: MarketDatasetBundle,
        requested_start_date: date,
        requested_end_date: date,
    ) -> AlignedMarketDataset:
        """Slice a dataset to common sessions at or before both boundaries."""
        if requested_start_date > requested_end_date:
            raise ValueError("start_date must be before or equal to end_date")

        common_index = None
        for series in bundle.dataset.series_by_symbol.values():
            common_index = (
                series.values.index
                if common_index is None
                else common_index.intersection(series.values.index)
            )

        assert common_index is not None
        start_candidates = common_index[
            (
                common_index.date
                >= MarketDatasetService.history_fetch_start(requested_start_date)
            )
            & (common_index.date <= requested_start_date)
        ]
        end_candidates = common_index[
            (
                common_index.date
                >= MarketDatasetService.history_fetch_start(requested_end_date)
            )
            & (common_index.date <= requested_end_date)
        ]

        if start_candidates.empty:
            raise InsufficientDataError(
                "no common trading session available within start boundary lookback"
            )
        if end_candidates.empty:
            raise InsufficientDataError(
                "no common trading session available within end boundary lookback"
            )

        effective_start = start_candidates[-1]
        effective_end = end_candidates[-1]

        if effective_start >= effective_end:
            raise InsufficientDataError(
                "effective period requires two distinct common sessions"
            )

        aligned_series = {
            symbol: MarketSeries(
                identifier=series.identifier,
                kind=series.kind,
                values=series.values.loc[effective_start:effective_end],
                unit=series.unit,
                metadata=dict(series.metadata),
            )
            for symbol, series in bundle.dataset.series_by_symbol.items()
        }

        return AlignedMarketDataset(
            dataset=MarketDataset(
                series_by_symbol=aligned_series,
                universe=bundle.dataset.universe,
            ),
            requested_start_date=requested_start_date,
            requested_end_date=requested_end_date,
            effective_start_date=effective_start.date(),
            effective_end_date=effective_end.date(),
            asset_symbols=bundle.asset_symbols,
            benchmark_symbol=bundle.benchmark_symbol,
        )

    @classmethod
    def history_fetch_start(cls, requested_start_date: date) -> date:
        """Include a bounded window for previous-session resolution."""
        return requested_start_date - timedelta(days=cls.PREVIOUS_SESSION_LOOKBACK_DAYS)

    @staticmethod
    def _add_unique_series(
        series_by_symbol: dict[str, MarketSeries],
        series: MarketSeries,
    ) -> None:
        if series.identifier in series_by_symbol:
            raise ValueError(f"duplicate asset resolved to {series.identifier}")
        series_by_symbol[series.identifier] = series
