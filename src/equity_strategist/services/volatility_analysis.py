from datetime import date

from equity_strategist.compute.returns import (
    ReturnMethod,
    compute_returns,
)
from equity_strategist.compute.volatility import compute_volatility
from equity_strategist.domain.analysis_results import (
    VolatilityComparisonResult,
    VolatilityItem,
)
from equity_strategist.domain.market_dataset import (
    AlignedMarketDataset,
    MarketDatasetBundle,
)
from equity_strategist.services.market_dataset import (
    MarketDatasetService,
)


class VolatilityAnalysisService:
    """Compare historical volatility across several assets."""

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
        annualization_factor: int = 252,
        return_method: ReturnMethod = ReturnMethod.LOG,
    ) -> VolatilityComparisonResult:
        """Compare annualized volatility across several assets."""
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
        return self.compare_aligned(aligned, annualization_factor, return_method)

    def compare_aligned(
        self,
        aligned: AlignedMarketDataset,
        annualization_factor: int = 252,
        return_method: ReturnMethod = ReturnMethod.LOG,
    ) -> VolatilityComparisonResult:
        """Compare volatility using an execution-level aligned dataset."""
        dataset = aligned.asset_dataset

        items: list[VolatilityItem] = []

        for price_series in dataset.series_by_symbol.values():
            return_series = compute_returns(
                price_series=price_series,
                method=return_method,
            )

            volatility = compute_volatility(
                return_series=return_series,
                annualization_factor=annualization_factor,
            )

            asset = price_series.metadata["asset"]

            items.append(
                VolatilityItem(
                    symbol=asset.symbol,
                    name=asset.name,
                    volatility=volatility,
                    currency=asset.currency,
                    observation_count=return_series.observation_count,
                )
            )

        ranked_items = tuple(
            sorted(
                items,
                key=lambda item: item.volatility,
                reverse=True,
            )
        )

        return VolatilityComparisonResult(
            start_date=aligned.requested_start_date,
            end_date=aligned.requested_end_date,
            annualization_factor=annualization_factor,
            items=ranked_items,
            effective_start_date=aligned.effective_start_date,
            effective_end_date=aligned.effective_end_date,
            price_field=next(iter(dataset.series_by_symbol.values())).metadata.get(
                "field", "adjusted_close"
            ),
            return_method=return_method.value,
        )
