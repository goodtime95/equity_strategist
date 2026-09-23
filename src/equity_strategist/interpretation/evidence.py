from equity_strategist.domain.analysis_execution import (
    AnalysisExecutionResult,
)
from equity_strategist.domain.analysis_results import (
    CorrelationAnalysisResult,
    DrawdownComparisonResult,
    PerformanceAnalysisResult,
    PerformanceItem,
    PerformancePeriodResult,
    RankingItem,
    RankingResult,
    VolatilityComparisonResult,
)
from equity_strategist.domain.results import PriceOnDateResult
from equity_strategist.interpretation.presentation import add_display_values


def serialize_execution_evidence(
    execution: AnalysisExecutionResult,
) -> dict[str, object]:
    """Serialize deterministic execution results into LLM-safe evidence."""
    return {
        "steps": [
            {
                "capability": step.capability.value,
                "result": _serialize_result(step.result),
            }
            for step in execution.step_results
        ]
    }


def _serialize_result(result: object) -> dict[str, object]:
    evidence = _serialize_raw_result(result)
    add_display_values(evidence)
    return evidence


def _serialize_raw_result(result: object) -> dict[str, object]:
    if isinstance(result, PriceOnDateResult):
        return _without_none(
            {
                "type": "price_on_date",
                "metric": "price",
                "symbol": result.asset.symbol,
                "name": result.asset.name,
                "currency": result.asset.currency,
                "requested_date": result.requested_date.isoformat(),
                "effective_date": result.effective_date.isoformat(),
                "price": str(result.price),
                "price_type": result.price_type,
                "used_previous_session": result.used_previous_session,
            }
        )

    if isinstance(result, PerformanceAnalysisResult):
        return _without_none(
            {
                "type": "performance_analysis",
                "metric": "performance",
                "measure": result.measure.value,
                "price_field": result.price_field,
                "return_method": result.return_method,
                "annualization_factor": result.annualization_factor,
                "ranking_direction": (
                    result.ranking_direction.value
                    if result.ranking_direction is not None
                    else None
                ),
                "top_n": result.top_n,
                "periods": [
                    _serialize_performance_period(period) for period in result.periods
                ],
            }
        )

    if isinstance(result, VolatilityComparisonResult):
        return _without_none(
            {
                "type": "volatility_comparison",
                "metric": "volatility",
                "start_date": result.start_date.isoformat(),
                "end_date": result.end_date.isoformat(),
                "annualization_factor": result.annualization_factor,
                "effective_start_date": _optional_date(result.effective_start_date),
                "effective_end_date": _optional_date(result.effective_end_date),
                "price_field": result.price_field,
                "return_method": result.return_method,
                "items": [
                    _without_none(
                        {
                            "symbol": item.symbol,
                            "name": item.name,
                            "value": str(item.volatility),
                            "currency": item.currency,
                            "observation_count": item.observation_count,
                        }
                    )
                    for item in result.items
                ],
            }
        )

    if isinstance(result, CorrelationAnalysisResult):
        return _without_none(
            {
                "type": "correlation_analysis",
                "metric": "correlation",
                "start_date": result.start_date.isoformat(),
                "end_date": result.end_date.isoformat(),
                "effective_start_date": _optional_date(result.effective_start_date),
                "effective_end_date": _optional_date(result.effective_end_date),
                "price_field": result.price_field,
                "return_method": result.return_method,
                "items": [
                    _without_none(
                        {
                            "first_symbol": item.first_symbol,
                            "first_name": item.first_name,
                            "second_symbol": item.second_symbol,
                            "second_name": item.second_name,
                            "value": str(item.correlation),
                            "observation_count": item.observation_count,
                            "first_currency": item.first_currency,
                            "second_currency": item.second_currency,
                        }
                    )
                    for item in result.items
                ],
            }
        )

    if isinstance(result, DrawdownComparisonResult):
        return _without_none(
            {
                "type": "drawdown_comparison",
                "metric": "maximum_drawdown",
                "start_date": result.start_date.isoformat(),
                "end_date": result.end_date.isoformat(),
                "effective_start_date": _optional_date(result.effective_start_date),
                "effective_end_date": _optional_date(result.effective_end_date),
                "price_field": result.price_field,
                "items": [
                    _without_none(
                        {
                            "symbol": item.symbol,
                            "name": item.name,
                            "value": str(item.maximum_drawdown),
                            "peak_date": item.peak_date.isoformat(),
                            "trough_date": item.trough_date.isoformat(),
                            "recovery_date": (
                                item.recovery_date.isoformat()
                                if item.recovery_date is not None
                                else None
                            ),
                            "currency": item.currency,
                            "observation_count": item.observation_count,
                        }
                    )
                    for item in result.items
                ],
            }
        )

    if isinstance(result, RankingResult):
        return _without_none(
            {
                "type": "ranking",
                "comparison_items": [
                    _serialize_ranking_item(item)
                    for item in getattr(result, "comparison_items", ())
                ],
                "metric": result.metric,
                "start_date": result.start_date.isoformat(),
                "end_date": result.end_date.isoformat(),
                "effective_start_date": _optional_date(result.effective_start_date),
                "effective_end_date": _optional_date(result.effective_end_date),
                "price_field": result.price_field,
                "return_method": result.return_method,
                "annualization_factor": result.annualization_factor,
                "items": [_serialize_ranking_item(item) for item in result.items],
            }
        )

    raise ValueError(f"unsupported execution result: {type(result).__name__}")


def _serialize_performance_period(period: PerformancePeriodResult) -> dict[str, object]:
    benchmark = None
    if period.benchmark is not None:
        benchmark = {
            "symbol": period.benchmark.symbol,
            "name": period.benchmark.name,
            "currency": period.benchmark.currency,
            "observation_count": period.benchmark.observation_count,
            "total_performance": str(period.benchmark.total_performance),
            "value": str(period.benchmark.value),
        }
    return {
        "horizon": period.horizon.value if period.horizon is not None else None,
        "requested_start_date": period.requested_start_date.isoformat(),
        "requested_end_date": period.requested_end_date.isoformat(),
        "effective_start_date": period.effective_start_date.isoformat(),
        "effective_end_date": period.effective_end_date.isoformat(),
        "benchmark": benchmark,
        "items": [_serialize_performance_item(item) for item in period.items],
        "comparison_items": [
            _serialize_performance_item(item)
            for item in getattr(period, "comparison_items", ())
        ],
        "currency_convention": "native_returns_no_fx_conversion",
        "currency_metadata_complete": all(
            item.currency is not None
            for item in (getattr(period, "comparison_items", ()) or period.items)
        )
        and (period.benchmark is None or period.benchmark.currency is not None),
    }


def _optional_date(value) -> str | None:
    return value.isoformat() if value is not None else None


def _without_none(values: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in values.items() if value is not None}


def _serialize_performance_item(item: PerformanceItem) -> dict[str, object]:
    return {
        "rank": item.rank,
        "symbol": item.symbol,
        "name": item.name,
        "currency": item.currency,
        "observation_count": item.observation_count,
        "total_performance": str(item.total_performance),
        "asset_performance": (
            str(item.asset_performance) if item.asset_performance is not None else None
        ),
        "benchmark_performance": (
            str(item.benchmark_performance)
            if item.benchmark_performance is not None
            else None
        ),
        "value": str(item.value),
    }


def _serialize_ranking_item(item: RankingItem) -> dict[str, object]:
    return _without_none(
        {
            "rank": item.rank,
            "symbol": item.symbol,
            "name": item.name,
            "value": str(item.value),
            "currency": item.currency,
            "observation_count": item.observation_count,
        }
    )
