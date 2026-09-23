from datetime import date

from equity_strategist.compute.returns import (
    ReturnMethod,
    compute_returns,
)
from equity_strategist.compute.volatility import (
    compute_volatility,
)
from equity_strategist.domain.analysis_request import (
    AnalysisHorizon,
    PerformanceMeasure,
    RankingDirection,
)
from equity_strategist.domain.analysis_results import (
    PerformanceAnalysisResult,
    RankingItem,
    RankingResult,
)
from equity_strategist.domain.asset import Asset
from equity_strategist.domain.market_dataset import (
    AlignedMarketDataset,
    MarketDatasetBundle,
)
from equity_strategist.services.market_dataset import (
    MarketDatasetService,
)
from equity_strategist.services.performance_analysis import PerformanceAnalysisService


class RankingAnalysisService:
    """Rank assets using deterministic financial metrics."""

    def __init__(
        self,
        market_dataset_service: MarketDatasetService,
        performance_analysis_service: PerformanceAnalysisService | None = None,
    ) -> None:
        self.market_dataset_service = market_dataset_service
        self.performance_analysis_service = (
            performance_analysis_service
            or PerformanceAnalysisService(market_dataset_service)
        )

    def rank_performance(
        self,
        asset_queries: list[str],
        start_date: date | None,
        end_date: date,
        ranking_direction: RankingDirection = RankingDirection.HIGHEST,
        top_n: int | None = None,
        performance_measure: PerformanceMeasure = PerformanceMeasure.TOTAL,
        horizons: tuple[AnalysisHorizon, ...] = (),
        benchmark: str | None = None,
    ) -> PerformanceAnalysisResult:
        if len(asset_queries) < 2:
            raise ValueError("at least two assets are required for ranking")

        self._validate_ranking_controls(ranking_direction, top_n)

        return self.performance_analysis_service.compare(
            asset_queries=asset_queries,
            start_date=start_date,
            end_date=end_date,
            performance_measure=performance_measure,
            horizons=horizons,
            benchmark=benchmark,
            ranking_direction=ranking_direction,
            top_n=top_n,
        )

    def rank_performance_for_assets(
        self,
        assets: tuple[Asset, ...],
        start_date: date | None,
        end_date: date,
        universe: str | None = None,
        ranking_direction: RankingDirection = RankingDirection.HIGHEST,
        top_n: int | None = None,
        performance_measure: PerformanceMeasure = PerformanceMeasure.TOTAL,
        horizons: tuple[AnalysisHorizon, ...] = (),
        benchmark: str | None = None,
    ) -> PerformanceAnalysisResult:
        if len(assets) < 2:
            raise ValueError("at least two assets are required for ranking")

        self._validate_ranking_controls(ranking_direction, top_n)

        return self.performance_analysis_service.compare_for_assets(
            assets=assets,
            start_date=start_date,
            end_date=end_date,
            universe=universe,
            performance_measure=performance_measure,
            horizons=horizons,
            benchmark=benchmark,
            ranking_direction=ranking_direction,
            top_n=top_n,
        )

    def rank_volatility(
        self,
        asset_queries: list[str],
        start_date: date,
        end_date: date,
        ranking_direction: RankingDirection = RankingDirection.HIGHEST,
        top_n: int | None = None,
    ) -> RankingResult:
        if len(asset_queries) < 2:
            raise ValueError("at least two assets are required for ranking")

        self._validate_ranking_controls(ranking_direction, top_n)

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
        return self.rank_volatility_aligned(
            aligned=aligned,
            ranking_direction=ranking_direction,
            top_n=top_n,
        )

    def rank_volatility_aligned(
        self,
        aligned: AlignedMarketDataset,
        ranking_direction: RankingDirection = RankingDirection.HIGHEST,
        top_n: int | None = None,
    ) -> RankingResult:
        """Rank volatility using an execution-level aligned dataset."""
        self._validate_ranking_controls(ranking_direction, top_n)
        dataset = aligned.asset_dataset

        raw_items = []

        for price_series in dataset.series_by_symbol.values():
            return_series = compute_returns(
                price_series=price_series,
                method=ReturnMethod.LOG,
            )

            volatility = compute_volatility(
                return_series=return_series,
                annualization_factor=252,
            )

            asset = price_series.metadata["asset"]

            raw_items.append(
                (
                    asset.symbol,
                    asset.name,
                    volatility,
                    asset.currency,
                    return_series.observation_count,
                )
            )

        raw_items.sort(
            key=lambda item: item[2],
            reverse=ranking_direction == RankingDirection.HIGHEST,
        )

        ranked_items = tuple(
            RankingItem(
                rank=rank,
                symbol=symbol,
                name=name,
                value=value,
                currency=currency,
                observation_count=observation_count,
            )
            for rank, (
                symbol,
                name,
                value,
                currency,
                observation_count,
            ) in enumerate(
                raw_items,
                start=1,
            )
        )

        return RankingResult(
            metric="volatility",
            start_date=aligned.requested_start_date,
            end_date=aligned.requested_end_date,
            items=ranked_items[:top_n],
            comparison_items=ranked_items,
            effective_start_date=aligned.effective_start_date,
            effective_end_date=aligned.effective_end_date,
            price_field=next(iter(dataset.series_by_symbol.values())).metadata.get(
                "field", "adjusted_close"
            ),
            return_method=ReturnMethod.LOG.value,
            annualization_factor=252,
        )

    @staticmethod
    def _validate_ranking_controls(
        ranking_direction: RankingDirection,
        top_n: int | None,
    ) -> None:
        if not isinstance(ranking_direction, RankingDirection):
            raise TypeError("ranking_direction must be a RankingDirection")

        if top_n is not None:
            if not isinstance(top_n, int) or isinstance(top_n, bool):
                raise TypeError("top_n must be an integer or None")

            if top_n < 1:
                raise ValueError("top_n must be greater than zero")
