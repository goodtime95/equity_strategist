from datetime import date

import pandas as pd
import pytest

from equity_strategist.domain.analysis_plan import AnalysisPlan, Capability, PlanStep
from equity_strategist.domain.analysis_request import (
    AnalysisHorizon,
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
    PerformanceMeasure,
    RankingDirection,
)
from equity_strategist.domain.asset import Asset
from equity_strategist.domain.market_series import MarketSeries, SeriesKind
from equity_strategist.services.market_dataset import MarketDatasetService
from equity_strategist.services.performance_analysis import PerformanceAnalysisService
from equity_strategist.services.volatility_analysis import VolatilityAnalysisService
from equity_strategist.strategists.executor import EquityExecutor


class FakeMarketSeriesService:
    def __init__(self, values_by_query: dict[str, dict[str, float]]) -> None:
        self.values_by_query = values_by_query
        self.calls: list[tuple[str, date, date]] = []

    def get_price_series(
        self,
        asset_query: str,
        start_date: date,
        end_date: date,
        preferred_exchange: str | None = None,
        preferred_currency: str | None = None,
        use_adjusted_close: bool = True,
    ) -> MarketSeries:
        self.calls.append((asset_query, start_date, end_date))
        asset = Asset(
            symbol=f"{asset_query}.TEST",
            name=asset_query,
            currency="EUR",
        )
        values = self.values_by_query[asset_query]
        return MarketSeries(
            identifier=asset.symbol,
            kind=SeriesKind.PRICE,
            values=pd.Series(
                list(values.values()),
                index=pd.to_datetime(list(values)),
            ),
            unit="EUR",
            metadata={"asset": asset, "field": "adjusted_close"},
        )


def build_service(
    values_by_query: dict[str, dict[str, float]],
) -> tuple[PerformanceAnalysisService, FakeMarketSeriesService]:
    series_service = FakeMarketSeriesService(values_by_query)
    dataset_service = MarketDatasetService(series_service)
    return PerformanceAnalysisService(dataset_service), series_service


def explicit_values() -> dict[str, dict[str, float]]:
    return {
        "Asset A": {
            "2023-12-29": 100.0,
            "2024-01-02": 110.0,
            "2024-01-05": 120.0,
        },
        "Asset B": {
            "2023-12-29": 100.0,
            "2024-01-03": 104.0,
            "2024-01-04": 108.0,
            "2024-01-05": 110.0,
        },
        "Benchmark": {
            "2023-12-29": 100.0,
            "2024-01-03": 102.0,
            "2024-01-05": 105.0,
        },
    }


def test_total_performance_uses_common_previous_session_endpoints() -> None:
    service, _ = build_service(explicit_values())

    result = service.compare(
        ["Asset A", "Asset B"],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 6),
    )

    period = result.periods[0]
    assert period.requested_start_date == date(2024, 1, 1)
    assert period.requested_end_date == date(2024, 1, 6)
    assert period.effective_start_date == date(2023, 12, 29)
    assert period.effective_end_date == date(2024, 1, 5)
    assert period.items[0].value == pytest.approx(0.2)
    assert period.items[0].total_performance == pytest.approx(0.2)
    assert {item.observation_count for item in period.items} == {3, 4}
    assert all(item.currency == "EUR" for item in period.items)
    assert result.price_field == "adjusted_close"
    assert result.return_method == "simple"


def test_annualized_performance_preserves_total_return() -> None:
    service, _ = build_service(explicit_values())

    result = service.compare(
        ["Asset A"],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 6),
        performance_measure=PerformanceMeasure.ANNUALIZED,
    )

    item = result.periods[0].items[0]
    expected = 1.2 ** (365.25 / 7) - 1.0
    assert item.value == pytest.approx(expected)
    assert item.total_performance == pytest.approx(0.2)
    assert result.annualization_factor == 365.25


def test_total_performance_executes_and_exposes_supplied_benchmark() -> None:
    service, series_service = build_service(explicit_values())

    result = service.compare(
        ["Asset A"],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 6),
        benchmark="Benchmark",
    )

    benchmark = result.periods[0].benchmark
    assert benchmark is not None
    assert benchmark.symbol == "Benchmark.TEST"
    assert benchmark.value == pytest.approx(0.05)
    assert benchmark.total_performance == pytest.approx(0.05)
    assert [call[0] for call in series_service.calls] == ["Asset A", "Benchmark"]


def test_annualized_performance_executes_and_exposes_supplied_benchmark() -> None:
    service, series_service = build_service(explicit_values())

    result = service.compare(
        ["Asset A"],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 6),
        performance_measure=PerformanceMeasure.ANNUALIZED,
        benchmark="Benchmark",
    )

    benchmark = result.periods[0].benchmark
    assert benchmark is not None
    assert benchmark.total_performance == pytest.approx(0.05)
    assert benchmark.value == pytest.approx(1.05 ** (365.25 / 7) - 1.0)
    assert [call[0] for call in series_service.calls] == ["Asset A", "Benchmark"]


@pytest.mark.parametrize(
    ("measure", "expected"),
    [
        (PerformanceMeasure.RELATIVE, 1.2 / 1.05 - 1.0),
        (PerformanceMeasure.EXCESS_RETURN, 0.2 - 0.05),
    ],
)
def test_benchmark_relative_measures_preserve_base_values(
    measure: PerformanceMeasure,
    expected: float,
) -> None:
    service, series_service = build_service(explicit_values())

    result = service.compare(
        ["Asset A"],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 6),
        performance_measure=measure,
        benchmark="Benchmark",
    )

    period = result.periods[0]
    item = period.items[0]
    assert item.asset_performance == pytest.approx(0.2)
    assert item.benchmark_performance == pytest.approx(0.05)
    assert item.value == pytest.approx(expected)
    assert period.benchmark is not None
    assert period.benchmark.total_performance == pytest.approx(0.05)
    assert [call[0] for call in series_service.calls] == ["Asset A", "Benchmark"]


def test_multi_horizon_downloads_longest_interval_once() -> None:
    values = {
        "Asset A": {
            "2022-01-04": 70.0,
            "2024-01-05": 80.0,
            "2024-12-05": 100.0,
            "2025-01-03": 110.0,
        },
        "Asset B": {
            "2022-01-04": 60.0,
            "2024-01-05": 75.0,
            "2024-12-05": 90.0,
            "2025-01-03": 99.0,
        },
    }
    service, series_service = build_service(values)

    result = service.compare(
        ["Asset A", "Asset B"],
        start_date=None,
        end_date=date(2025, 1, 5),
        horizons=(AnalysisHorizon.ONE_MONTH, AnalysisHorizon.THREE_YEARS),
    )

    assert [period.horizon for period in result.periods] == [
        AnalysisHorizon.ONE_MONTH,
        AnalysisHorizon.THREE_YEARS,
    ]
    assert result.periods[0].requested_start_date == date(2024, 12, 5)
    assert result.periods[1].requested_start_date == date(2022, 1, 5)
    assert result.periods[1].effective_start_date == date(2022, 1, 4)
    assert len(series_service.calls) == 2
    assert all(call[1] == date(2021, 12, 26) for call in series_service.calls)


@pytest.mark.parametrize(
    ("horizon", "expected_start"),
    [
        (AnalysisHorizon.ONE_MONTH, date(2025, 2, 28)),
        (AnalysisHorizon.THREE_MONTHS, date(2024, 12, 31)),
        (AnalysisHorizon.SIX_MONTHS, date(2024, 9, 30)),
        (AnalysisHorizon.YEAR_TO_DATE, date(2025, 1, 1)),
        (AnalysisHorizon.ONE_YEAR, date(2024, 3, 31)),
        (AnalysisHorizon.THREE_YEARS, date(2022, 3, 31)),
    ],
)
def test_standard_horizons_resolve_from_calendar_anchor(
    horizon: AnalysisHorizon,
    expected_start: date,
) -> None:
    periods = PerformanceAnalysisService.resolve_requested_periods(
        start_date=None,
        end_date=date(2025, 3, 31),
        horizons=(horizon,),
    )

    assert periods[0].start_date == expected_start
    assert periods[0].end_date == date(2025, 3, 31)


def test_ranking_is_applied_independently_per_horizon() -> None:
    values = {
        "Asset A": {
            "2024-01-05": 100.0,
            "2024-12-05": 100.0,
            "2025-01-03": 120.0,
        },
        "Asset B": {
            "2024-01-05": 100.0,
            "2024-12-05": 80.0,
            "2025-01-03": 100.0,
        },
        "Asset C": {
            "2024-01-05": 100.0,
            "2024-12-05": 95.0,
            "2025-01-03": 105.0,
        },
    }
    service, _ = build_service(values)

    result = service.compare(
        list(values),
        start_date=None,
        end_date=date(2025, 1, 5),
        horizons=(AnalysisHorizon.ONE_MONTH, AnalysisHorizon.ONE_YEAR),
        ranking_direction=RankingDirection.LOWEST,
        top_n=1,
    )

    assert result.periods[0].items[0].symbol == "Asset C.TEST"
    assert result.periods[1].items[0].symbol == "Asset B.TEST"
    assert all(period.items[0].rank == 1 for period in result.periods)


def test_executor_reuses_one_dataset_for_compatible_metrics() -> None:
    service, series_service = build_service(explicit_values())
    dataset_service = service.market_dataset_service
    executor = EquityExecutor(
        volatility_analysis_service=VolatilityAnalysisService(dataset_service),
        performance_analysis_service=service,
        correlation_analysis_service=object(),  # type: ignore[arg-type]
        drawdown_analysis_service=object(),  # type: ignore[arg-type]
        ranking_analysis_service=object(),  # type: ignore[arg-type]
        market_query_service=object(),  # type: ignore[arg-type]
        universe_constituent_service=object(),  # type: ignore[arg-type]
        universe_asset_resolver=object(),  # type: ignore[arg-type]
        market_dataset_service=dataset_service,
    )
    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(AnalysisMetric.PERFORMANCE, AnalysisMetric.VOLATILITY),
        assets=("Asset A", "Asset B"),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 6),
    )
    plan = AnalysisPlan(
        request,
        (
            PlanStep(Capability.COMPARE_PERFORMANCE),
            PlanStep(Capability.COMPARE_VOLATILITY),
        ),
    )

    execution = executor.execute(plan)

    assert len(execution.step_results) == 2
    assert [call[0] for call in series_service.calls] == ["Asset A", "Asset B"]
