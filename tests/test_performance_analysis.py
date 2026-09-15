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
        existing_series: dict[str, MarketSeries] | None = None,
    ) -> MarketSeries:
        symbol = f"{asset_query}.TEST"
        if existing_series is not None and symbol in existing_series:
            return existing_series[symbol]
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
            ).loc[str(start_date) : str(end_date)],
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


@pytest.mark.parametrize(
    "companion", [None, AnalysisHorizon.ONE_YEAR, AnalysisHorizon.THREE_YEARS]
)
@pytest.mark.parametrize("start_session", ["2024-12-20", "2024-12-21", "2024-12-31"])
def test_horizon_boundary_eligibility_is_independent_of_download_breadth(
    companion: AnalysisHorizon | None,
    start_session: str,
) -> None:
    service, provider = build_service(
        {
            "Asset A": {
                "2022-01-31": 50.0,
                "2024-01-31": 80.0,
                start_session: 100.0,
                "2025-01-15": 110.0,
                "2025-01-31": 120.0,
            }
        }
    )
    horizons = (AnalysisHorizon.ONE_MONTH,) + ((companion,) if companion else ())
    if start_session == "2024-12-20":
        with pytest.raises(ValueError, match="start boundary lookback"):
            service.compare(["Asset A"], None, date(2025, 1, 31), horizons=horizons)
    else:
        result = service.compare(
            ["Asset A"], None, date(2025, 1, 31), horizons=horizons
        )
        period = result.periods[0]
        assert period.requested_start_date == date(2024, 12, 31)
        assert period.effective_start_date == date.fromisoformat(start_session)
        assert period.effective_end_date == date(2025, 1, 31)
        assert period.items[0].value == pytest.approx(0.2)
    assert len(provider.calls) == 1


@pytest.mark.parametrize("last_session", ["2025-01-20", "2025-01-21"])
def test_end_boundary_has_its_own_inclusive_lookback(last_session: str) -> None:
    service, _ = build_service(
        {
            "Asset A": {
                "2024-12-31": 100.0,
                last_session: 120.0,
            }
        }
    )
    if last_session == "2025-01-20":
        with pytest.raises(ValueError, match="end boundary lookback"):
            service.compare(
                ["Asset A"],
                None,
                date(2025, 1, 31),
                horizons=(AnalysisHorizon.ONE_MONTH,),
            )
    else:
        result = service.compare(
            ["Asset A"], None, date(2025, 1, 31), horizons=(AnalysisHorizon.ONE_MONTH,)
        )
        assert result.periods[0].effective_end_date == date(2025, 1, 21)


def test_ytd_uses_previous_year_close() -> None:
    service, _ = build_service(explicit_values())
    result = service.compare(
        ["Asset A", "Asset B"],
        None,
        date(2024, 1, 6),
        horizons=(AnalysisHorizon.YEAR_TO_DATE,),
    )
    assert result.periods[0].requested_start_date == date(2024, 1, 1)
    assert result.periods[0].effective_start_date == date(2023, 12, 29)
    assert result.items[0].value == pytest.approx(0.2)


@pytest.mark.parametrize("universe", [False, True])
@pytest.mark.parametrize(
    "measure",
    [
        PerformanceMeasure.TOTAL,
        PerformanceMeasure.RELATIVE,
        PerformanceMeasure.EXCESS_RETURN,
    ],
)
def test_executor_reuses_asset_as_benchmark(
    universe: bool, measure: PerformanceMeasure
) -> None:
    from decimal import Decimal
    from types import SimpleNamespace

    from equity_strategist.domain.observations import DailyPriceObservation
    from equity_strategist.domain.request_validation import RequestStatus
    from equity_strategist.services.market_series import MarketSeriesService
    from equity_strategist.services.ranking_analysis import RankingAnalysisService
    from equity_strategist.strategists.planner import EquityPlanner
    from equity_strategist.strategists.validator import AnalysisRequestValidator

    assets = (
        Asset("A", name="Asset A", currency="EUR"),
        Asset("B", name="Asset B", currency="EUR"),
    )
    downloads: list[str] = []

    def resolve(query: str, **kwargs: object) -> Asset:
        return assets[0] if query in {"Asset A", "A", "benchmark alias"} else assets[1]

    def get_daily_prices(
        asset: Asset, start_date: date, end_date: date
    ) -> list[DailyPriceObservation]:
        downloads.append(asset.symbol)
        return [
            DailyPriceObservation(
                asset, day, value, value, value, value, adjusted_close=value
            )
            for day, value in [
                (date(2023, 12, 29), Decimal("100")),
                (
                    date(2024, 1, 5),
                    Decimal("120") if asset.symbol == "A" else Decimal("110"),
                ),
            ]
        ]

    dataset = MarketDatasetService(
        MarketSeriesService(
            SimpleNamespace(get_daily_prices=get_daily_prices),
            SimpleNamespace(resolve=resolve),
        )
    )
    performance = PerformanceAnalysisService(dataset)
    executor = EquityExecutor(
        volatility_analysis_service=object(),
        performance_analysis_service=performance,
        correlation_analysis_service=object(),
        drawdown_analysis_service=object(),
        ranking_analysis_service=RankingAnalysisService(dataset, performance),
        market_query_service=object(),
        universe_constituent_service=SimpleNamespace(
            get_constituents=lambda name: ("Asset A", "Asset B")
        ),
        universe_asset_resolver=SimpleNamespace(resolve_many=lambda queries: assets),
        market_dataset_service=dataset,
    )
    request = AnalysisRequest(
        objective=AnalysisObjective.RANK,
        metrics=(AnalysisMetric.PERFORMANCE,),
        assets=() if universe else ("Asset A", "Asset B"),
        universe="Test universe" if universe else None,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 6),
        benchmark="benchmark alias",
        performance_measure=measure,
    )
    assert AnalysisRequestValidator().validate(request).status == RequestStatus.READY
    result = executor.execute(EquityPlanner().plan(request)).step_results[0].result
    assert downloads == ["A", "B"]
    assert result.periods[0].benchmark.symbol == "A"
    item = next(item for item in result.items if item.symbol == "A")
    assert item.value == pytest.approx(
        0.2 if measure == PerformanceMeasure.TOTAL else 0.0
    )

    with pytest.raises(ValueError, match="duplicate asset"):
        if universe:
            dataset.build_price_dataset_bundle_for_assets(
                (assets[0], assets[0]),
                date(2023, 12, 29),
                date(2024, 1, 5),
                benchmark_query="benchmark alias",
            )
        else:
            dataset.build_price_dataset_bundle(
                ["Asset A", "A"],
                date(2023, 12, 29),
                date(2024, 1, 5),
                benchmark_query="benchmark alias",
            )
