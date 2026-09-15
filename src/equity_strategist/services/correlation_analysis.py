from datetime import date
from itertools import combinations

from equity_strategist.compute.correlation import compute_correlation
from equity_strategist.compute.returns import (
    ReturnMethod,
    compute_returns,
)
from equity_strategist.domain.analysis_results import (
    CorrelationAnalysisResult,
    CorrelationItem,
)
from equity_strategist.domain.market_dataset import (
    AlignedMarketDataset,
    MarketDatasetBundle,
)
from equity_strategist.services.market_dataset import (
    MarketDatasetService,
)


class CorrelationAnalysisService:
    """Compute pairwise historical correlations across several assets."""

    def __init__(
        self,
        market_dataset_service: MarketDatasetService,
    ) -> None:
        self.market_dataset_service = market_dataset_service

    def analyze(
        self,
        asset_queries: list[str],
        start_date: date,
        end_date: date,
        return_method: ReturnMethod = ReturnMethod.LOG,
    ) -> CorrelationAnalysisResult:
        if len(asset_queries) < 2:
            raise ValueError(
                "at least two assets are required for correlation analysis"
            )

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
        return self.analyze_aligned(aligned, return_method)

    def analyze_aligned(
        self,
        aligned: AlignedMarketDataset,
        return_method: ReturnMethod = ReturnMethod.LOG,
    ) -> CorrelationAnalysisResult:
        """Analyze correlations using an execution-level aligned dataset."""
        dataset = aligned.asset_dataset

        return_series_by_symbol = {}

        for symbol, price_series in dataset.series_by_symbol.items():
            return_series_by_symbol[symbol] = compute_returns(
                price_series=price_series,
                method=return_method,
            )

        items: list[CorrelationItem] = []

        for first_symbol, second_symbol in combinations(
            return_series_by_symbol,
            2,
        ):
            first_series = return_series_by_symbol[first_symbol]
            second_series = return_series_by_symbol[second_symbol]

            correlation = compute_correlation(
                first_series=first_series,
                second_series=second_series,
            )
            observation_count = len(
                first_series.values.index.intersection(second_series.values.index)
            )

            first_asset = first_series.metadata["asset"]
            second_asset = second_series.metadata["asset"]

            items.append(
                CorrelationItem(
                    first_symbol=first_asset.symbol,
                    first_name=first_asset.name,
                    second_symbol=second_asset.symbol,
                    second_name=second_asset.name,
                    correlation=correlation,
                    observation_count=observation_count,
                    first_currency=first_asset.currency,
                    second_currency=second_asset.currency,
                )
            )

        return CorrelationAnalysisResult(
            start_date=aligned.requested_start_date,
            end_date=aligned.requested_end_date,
            items=tuple(items),
            effective_start_date=aligned.effective_start_date,
            effective_end_date=aligned.effective_end_date,
            price_field=next(iter(dataset.series_by_symbol.values())).metadata.get(
                "field", "adjusted_close"
            ),
            return_method=return_method.value,
        )
