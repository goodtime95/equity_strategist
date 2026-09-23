import calendar
from dataclasses import dataclass
from datetime import date

from equity_strategist.compute.performance import (
    compute_annualized_performance,
    compute_total_performance,
)
from equity_strategist.domain.analysis_request import (
    AnalysisHorizon,
    PerformanceMeasure,
    RankingDirection,
)
from equity_strategist.domain.analysis_results import (
    PerformanceAnalysisResult,
    PerformanceBenchmark,
    PerformanceItem,
    PerformancePeriodResult,
)
from equity_strategist.domain.asset import Asset
from equity_strategist.domain.errors import InsufficientDataError
from equity_strategist.domain.market_dataset import (
    AlignedMarketDataset,
    MarketDatasetBundle,
)
from equity_strategist.services.market_dataset import MarketDatasetService


@dataclass(frozen=True, slots=True)
class RequestedPerformancePeriod:
    horizon: AnalysisHorizon | None
    start_date: date
    end_date: date


class PerformanceAnalysisService:
    """Calculate deterministic performance over explicit or standard periods."""

    def __init__(self, market_dataset_service: MarketDatasetService) -> None:
        self.market_dataset_service = market_dataset_service

    def compare(
        self,
        asset_queries: list[str],
        start_date: date | None,
        end_date: date,
        performance_measure: PerformanceMeasure = PerformanceMeasure.TOTAL,
        horizons: tuple[AnalysisHorizon, ...] = (),
        benchmark: str | None = None,
        ranking_direction: RankingDirection | None = None,
        top_n: int | None = None,
    ) -> PerformanceAnalysisResult:
        if not asset_queries:
            raise ValueError("at least one asset is required for performance analysis")

        periods = self.resolve_requested_periods(start_date, end_date, horizons)
        fetch_start = MarketDatasetService.history_fetch_start(
            min(period.start_date for period in periods)
        )
        if benchmark is None:
            dataset = self.market_dataset_service.build_price_dataset(
                asset_queries=asset_queries,
                start_date=fetch_start,
                end_date=end_date,
            )
            bundle = MarketDatasetBundle(dataset, dataset.symbols)
        else:
            bundle = self.market_dataset_service.build_price_dataset_bundle(
                asset_queries=asset_queries,
                start_date=fetch_start,
                end_date=end_date,
                benchmark_query=benchmark,
            )
        return self.analyze_bundle(
            bundle=bundle,
            periods=periods,
            performance_measure=performance_measure,
            ranking_direction=ranking_direction,
            top_n=top_n,
        )

    def compare_for_assets(
        self,
        assets: tuple[Asset, ...],
        start_date: date | None,
        end_date: date,
        performance_measure: PerformanceMeasure = PerformanceMeasure.TOTAL,
        horizons: tuple[AnalysisHorizon, ...] = (),
        benchmark: str | None = None,
        universe: str | None = None,
        ranking_direction: RankingDirection | None = None,
        top_n: int | None = None,
    ) -> PerformanceAnalysisResult:
        periods = self.resolve_requested_periods(start_date, end_date, horizons)
        fetch_start = MarketDatasetService.history_fetch_start(
            min(period.start_date for period in periods)
        )
        if benchmark is None:
            dataset = self.market_dataset_service.build_price_dataset_for_assets(
                assets=assets,
                start_date=fetch_start,
                end_date=end_date,
                universe=universe,
            )
            bundle = MarketDatasetBundle(dataset, dataset.symbols)
        else:
            bundle = self.market_dataset_service.build_price_dataset_bundle_for_assets(
                assets=assets,
                start_date=fetch_start,
                end_date=end_date,
                benchmark_query=benchmark,
                universe=universe,
            )
        return self.analyze_bundle(
            bundle=bundle,
            periods=periods,
            performance_measure=performance_measure,
            ranking_direction=ranking_direction,
            top_n=top_n,
        )

    def analyze_bundle(
        self,
        bundle: MarketDatasetBundle,
        periods: tuple[RequestedPerformancePeriod, ...],
        performance_measure: PerformanceMeasure,
        ranking_direction: RankingDirection | None = None,
        top_n: int | None = None,
    ) -> PerformanceAnalysisResult:
        """Calculate all requested periods from one downloaded dataset."""
        self._validate_measure(performance_measure, bundle.benchmark_symbol)
        period_results = tuple(
            self._analyze_period(
                aligned=MarketDatasetService.align_price_dataset(
                    bundle=bundle,
                    requested_start_date=period.start_date,
                    requested_end_date=period.end_date,
                ),
                horizon=period.horizon,
                measure=performance_measure,
                ranking_direction=ranking_direction,
                top_n=top_n,
            )
            for period in periods
        )
        return PerformanceAnalysisResult(
            measure=performance_measure,
            periods=period_results,
            price_field=next(
                iter(bundle.dataset.series_by_symbol.values())
            ).metadata.get("field", "adjusted_close"),
            annualization_factor=(
                365.25 if performance_measure == PerformanceMeasure.ANNUALIZED else None
            ),
            ranking_direction=ranking_direction,
            top_n=top_n,
        )

    def _analyze_period(
        self,
        aligned: AlignedMarketDataset,
        horizon: AnalysisHorizon | None,
        measure: PerformanceMeasure,
        ranking_direction: RankingDirection | None,
        top_n: int | None,
    ) -> PerformancePeriodResult:
        benchmark_total = None
        benchmark_result = None

        if aligned.benchmark_symbol is not None:
            benchmark_series = aligned.dataset.get(aligned.benchmark_symbol)
            benchmark_total = compute_total_performance(benchmark_series)
            benchmark_asset = benchmark_series.metadata["asset"]
            benchmark_result = PerformanceBenchmark(
                symbol=benchmark_asset.symbol,
                name=benchmark_asset.name,
                currency=benchmark_asset.currency,
                observation_count=benchmark_series.observation_count,
                total_performance=benchmark_total,
                value=self._absolute_value(benchmark_series, measure),
            )

        raw_items: list[PerformanceItem] = []
        for symbol in aligned.asset_symbols:
            series = aligned.dataset.get(symbol)
            total = compute_total_performance(series)
            value = self._value(series, measure, total, benchmark_total)
            asset = series.metadata["asset"]
            is_relative = measure in {
                PerformanceMeasure.RELATIVE,
                PerformanceMeasure.EXCESS_RETURN,
            }
            raw_items.append(
                PerformanceItem(
                    symbol=asset.symbol,
                    name=asset.name,
                    currency=asset.currency,
                    observation_count=series.observation_count,
                    total_performance=total,
                    value=value,
                    asset_performance=total if is_relative else None,
                    benchmark_performance=benchmark_total if is_relative else None,
                )
            )

        raw_items.sort(
            key=lambda item: item.value,
            reverse=ranking_direction != RankingDirection.LOWEST,
        )

        if ranking_direction is not None:
            items = tuple(
                PerformanceItem(
                    symbol=item.symbol,
                    name=item.name,
                    currency=item.currency,
                    observation_count=item.observation_count,
                    total_performance=item.total_performance,
                    value=item.value,
                    rank=rank,
                    asset_performance=item.asset_performance,
                    benchmark_performance=item.benchmark_performance,
                )
                for rank, item in enumerate(raw_items, start=1)
            )
        else:
            items = tuple(raw_items)

        return PerformancePeriodResult(
            horizon=horizon,
            requested_start_date=aligned.requested_start_date,
            requested_end_date=aligned.requested_end_date,
            effective_start_date=aligned.effective_start_date,
            effective_end_date=aligned.effective_end_date,
            items=items[:top_n] if ranking_direction is not None else items,
            comparison_items=items if ranking_direction is not None else (),
            benchmark=benchmark_result,
        )

    @staticmethod
    def resolve_requested_periods(
        start_date: date | None,
        end_date: date,
        horizons: tuple[AnalysisHorizon, ...],
    ) -> tuple[RequestedPerformancePeriod, ...]:
        if horizons:
            return tuple(
                RequestedPerformancePeriod(
                    horizon=horizon,
                    start_date=_horizon_start(end_date, horizon),
                    end_date=end_date,
                )
                for horizon in horizons
            )
        if start_date is None:
            raise ValueError("start_date is required without horizons")
        return (RequestedPerformancePeriod(None, start_date, end_date),)

    @staticmethod
    def _absolute_value(series, measure: PerformanceMeasure) -> float:
        if measure == PerformanceMeasure.ANNUALIZED:
            return compute_annualized_performance(series)
        return compute_total_performance(series)

    @classmethod
    def _value(
        cls,
        series,
        measure: PerformanceMeasure,
        asset_total: float,
        benchmark_total: float | None,
    ) -> float:
        if measure == PerformanceMeasure.TOTAL:
            return asset_total
        if measure == PerformanceMeasure.ANNUALIZED:
            return compute_annualized_performance(series)
        assert benchmark_total is not None
        if measure == PerformanceMeasure.RELATIVE:
            if 1.0 + benchmark_total <= 0:
                raise InsufficientDataError(
                    "benchmark growth factor is not representable as positive"
                )
            return (1.0 + asset_total) / (1.0 + benchmark_total) - 1.0
        return asset_total - benchmark_total

    @staticmethod
    def _validate_measure(
        measure: PerformanceMeasure,
        benchmark_symbol: str | None,
    ) -> None:
        if not isinstance(measure, PerformanceMeasure):
            raise TypeError("performance_measure must be a PerformanceMeasure")
        if (
            measure
            in {
                PerformanceMeasure.RELATIVE,
                PerformanceMeasure.EXCESS_RETURN,
            }
            and benchmark_symbol is None
        ):
            raise ValueError(f"{measure.value} requires a benchmark")


def _horizon_start(anchor: date, horizon: AnalysisHorizon) -> date:
    if horizon == AnalysisHorizon.YEAR_TO_DATE:
        return date(anchor.year, 1, 1)
    months = {
        AnalysisHorizon.ONE_MONTH: 1,
        AnalysisHorizon.THREE_MONTHS: 3,
        AnalysisHorizon.SIX_MONTHS: 6,
        AnalysisHorizon.ONE_YEAR: 12,
        AnalysisHorizon.THREE_YEARS: 36,
    }[horizon]
    total_months = anchor.year * 12 + anchor.month - 1 - months
    year, zero_based_month = divmod(total_months, 12)
    month = zero_based_month + 1
    day = min(anchor.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)
