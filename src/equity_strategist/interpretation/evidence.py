from equity_strategist.domain.analysis_execution import (
    AnalysisExecutionResult,
)
from equity_strategist.domain.analysis_results import (
    CorrelationAnalysisResult,
    DrawdownComparisonResult,
    PerformanceComparisonResult,
    RankingResult,
    VolatilityComparisonResult,
)
from equity_strategist.domain.results import PriceOnDateResult


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
    if isinstance(result, PriceOnDateResult):
        return {
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

    if isinstance(result, PerformanceComparisonResult):
        return {
            "type": "performance_comparison",
            "metric": "performance",
            "start_date": result.start_date.isoformat(),
            "end_date": result.end_date.isoformat(),
            "items": [
                {
                    "symbol": item.symbol,
                    "name": item.name,
                    "value": str(item.performance),
                }
                for item in result.items
            ],
        }

    if isinstance(result, VolatilityComparisonResult):
        return {
            "type": "volatility_comparison",
            "metric": "volatility",
            "start_date": result.start_date.isoformat(),
            "end_date": result.end_date.isoformat(),
            "annualization_factor": result.annualization_factor,
            "items": [
                {
                    "symbol": item.symbol,
                    "name": item.name,
                    "value": str(item.volatility),
                }
                for item in result.items
            ],
        }

    if isinstance(result, CorrelationAnalysisResult):
        return {
            "type": "correlation_analysis",
            "metric": "correlation",
            "start_date": result.start_date.isoformat(),
            "end_date": result.end_date.isoformat(),
            "items": [
                {
                    "first_symbol": item.first_symbol,
                    "first_name": item.first_name,
                    "second_symbol": item.second_symbol,
                    "second_name": item.second_name,
                    "value": str(item.correlation),
                }
                for item in result.items
            ],
        }

    if isinstance(result, DrawdownComparisonResult):
        return {
            "type": "drawdown_comparison",
            "metric": "maximum_drawdown",
            "start_date": result.start_date.isoformat(),
            "end_date": result.end_date.isoformat(),
            "items": [
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
                }
                for item in result.items
            ],
        }

    if isinstance(result, RankingResult):
        return {
            "type": "ranking",
            "metric": result.metric,
            "start_date": result.start_date.isoformat(),
            "end_date": result.end_date.isoformat(),
            "items": [
                {
                    "rank": item.rank,
                    "symbol": item.symbol,
                    "name": item.name,
                    "value": str(item.value),
                }
                for item in result.items
            ],
        }

    raise ValueError(f"unsupported execution result: {type(result).__name__}")
