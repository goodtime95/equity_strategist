from datetime import date

from equity_strategist.compute.drawdown import (
    compute_maximum_drawdown,
)
from equity_strategist.domain.analysis_results import (
    DrawdownComparisonResult,
    DrawdownItem,
)
from equity_strategist.domain.market_dataset import (
    AlignedMarketDataset,
    MarketDatasetBundle,
)
from equity_strategist.services.market_dataset import (
    MarketDatasetService,
)


class DrawdownAnalysisService:
    """Compare maximum drawdowns across several assets."""

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
    ) -> DrawdownComparisonResult:
        if len(asset_queries) < 2:
            raise ValueError("at least two assets are required for comparison")

        dataset = self.market_dataset_service.build_price_dataset(
            asset_queries=asset_queries,
            start_date=MarketDatasetService.history_fetch_start(start_date),
            end_date=end_date,
        )
        aligned = MarketDatasetService.align_price_dataset(
            bundle=MarketDatasetBundle(dataset, dataset.symbols),
            requested_start_date=start_date,
            requested_end_date=end_date,
        )
        return self.compare_aligned(aligned)

    def compare_aligned(
        self,
        aligned: AlignedMarketDataset,
    ) -> DrawdownComparisonResult:
        """Compare drawdowns using an execution-level aligned dataset."""
        dataset = aligned.asset_dataset

        items: list[DrawdownItem] = []

        for price_series in dataset.series_by_symbol.values():
            result = compute_maximum_drawdown(price_series)

            asset = price_series.metadata["asset"]

            recovery_date = (
                result.recovery_date.date()
                if result.recovery_date is not None
                else None
            )

            items.append(
                DrawdownItem(
                    symbol=asset.symbol,
                    name=asset.name,
                    maximum_drawdown=result.maximum_drawdown,
                    peak_date=result.peak_date.date(),
                    trough_date=result.trough_date.date(),
                    recovery_date=recovery_date,
                    currency=asset.currency,
                    observation_count=price_series.observation_count,
                )
            )

        ranked_items = tuple(
            sorted(
                items,
                key=lambda item: item.maximum_drawdown,
            )
        )

        return DrawdownComparisonResult(
            start_date=aligned.requested_start_date,
            end_date=aligned.requested_end_date,
            items=ranked_items,
            effective_start_date=aligned.effective_start_date,
            effective_end_date=aligned.effective_end_date,
            price_field=next(iter(dataset.series_by_symbol.values())).metadata.get(
                "field", "adjusted_close"
            ),
        )
