from datetime import date

from equity_strategist.compute.performance import (
    compute_total_performance,
)
from equity_strategist.domain.analysis_results import (
    PerformanceComparisonResult,
    PerformanceItem,
)
from equity_strategist.services.market_dataset import (
    MarketDatasetService,
)


class PerformanceAnalysisService:
    """Compare historical performance across several assets."""

    def __init__(
        self,
        market_dataset_service: MarketDatasetService,
    ) -> None:
        self.market_dataset_service = market_dataset_service

    def compare(
        self,
        asset_queries: list[str],
        start_date: date,
        end_date: date,
    ) -> PerformanceComparisonResult:
        if len(asset_queries) < 2:
            raise ValueError("at least two assets are required for comparison")

        dataset = self.market_dataset_service.build_price_dataset(
            asset_queries=asset_queries,
            start_date=start_date,
            end_date=end_date,
        )

        items: list[PerformanceItem] = []

        for price_series in dataset.series_by_symbol.values():
            performance = compute_total_performance(price_series)

            asset = price_series.metadata["asset"]

            items.append(
                PerformanceItem(
                    symbol=asset.symbol,
                    name=asset.name,
                    performance=performance,
                )
            )

        ranked_items = tuple(
            sorted(
                items,
                key=lambda item: item.performance,
                reverse=True,
            )
        )

        return PerformanceComparisonResult(
            start_date=start_date,
            end_date=end_date,
            items=ranked_items,
        )
