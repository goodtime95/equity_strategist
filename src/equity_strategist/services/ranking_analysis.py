from datetime import date

from equity_strategist.compute.performance import (
    compute_total_performance,
)
from equity_strategist.compute.returns import (
    ReturnMethod,
    compute_returns,
)
from equity_strategist.compute.volatility import (
    compute_volatility,
)
from equity_strategist.domain.analysis_request import RankingDirection
from equity_strategist.domain.analysis_results import (
    RankingItem,
    RankingResult,
)
from equity_strategist.domain.asset import Asset
from equity_strategist.domain.market_dataset import MarketDataset
from equity_strategist.services.market_dataset import (
    MarketDatasetService,
)


class RankingAnalysisService:
    """Rank assets using deterministic financial metrics."""

    def __init__(
        self,
        market_dataset_service: MarketDatasetService,
    ) -> None:
        self.market_dataset_service = market_dataset_service

    def rank_performance(
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
            start_date=start_date,
            end_date=end_date,
        )

        return self._rank_performance_dataset(
            dataset=dataset,
            start_date=start_date,
            end_date=end_date,
            ranking_direction=ranking_direction,
            top_n=top_n,
        )

    def rank_performance_for_assets(
        self,
        assets: tuple[Asset, ...],
        start_date: date,
        end_date: date,
        universe: str | None = None,
        ranking_direction: RankingDirection = RankingDirection.HIGHEST,
        top_n: int | None = None,
    ) -> RankingResult:
        if len(assets) < 2:
            raise ValueError("at least two assets are required for ranking")

        self._validate_ranking_controls(ranking_direction, top_n)

        dataset = self.market_dataset_service.build_price_dataset_for_assets(
            assets=assets,
            start_date=start_date,
            end_date=end_date,
            universe=universe,
        )

        return self._rank_performance_dataset(
            dataset=dataset,
            start_date=start_date,
            end_date=end_date,
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
            start_date=start_date,
            end_date=end_date,
        )

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
                )
            )

        raw_items.sort(
            key=lambda item: item[2],
            reverse=ranking_direction == RankingDirection.HIGHEST,
        )
        selected_items = raw_items[:top_n]

        ranked_items = tuple(
            RankingItem(
                rank=rank,
                symbol=symbol,
                name=name,
                value=value,
            )
            for rank, (
                symbol,
                name,
                value,
            ) in enumerate(
                selected_items,
                start=1,
            )
        )

        return RankingResult(
            metric="volatility",
            start_date=start_date,
            end_date=end_date,
            items=ranked_items,
        )

    @staticmethod
    def _rank_performance_dataset(
        dataset: MarketDataset,
        start_date: date,
        end_date: date,
        ranking_direction: RankingDirection,
        top_n: int | None,
    ) -> RankingResult:
        raw_items = []

        for price_series in dataset.series_by_symbol.values():
            performance = compute_total_performance(price_series)

            asset = price_series.metadata["asset"]

            raw_items.append(
                (
                    asset.symbol,
                    asset.name,
                    performance,
                )
            )

        raw_items.sort(
            key=lambda item: item[2],
            reverse=ranking_direction == RankingDirection.HIGHEST,
        )
        selected_items = raw_items[:top_n]

        ranked_items = tuple(
            RankingItem(
                rank=rank,
                symbol=symbol,
                name=name,
                value=value,
            )
            for rank, (
                symbol,
                name,
                value,
            ) in enumerate(
                selected_items,
                start=1,
            )
        )

        return RankingResult(
            metric="performance",
            start_date=start_date,
            end_date=end_date,
            items=ranked_items,
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
