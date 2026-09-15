from datetime import date

from equity_strategist.domain.analysis_execution import (
    AnalysisExecutionResult,
)
from equity_strategist.domain.analysis_results import (
    CorrelationAnalysisResult,
    DrawdownComparisonResult,
    PerformanceAnalysisResult,
    RankingResult,
    VolatilityComparisonResult,
)
from equity_strategist.domain.request_validation import (
    RequestStatus,
    RequestValidationResult,
)
from equity_strategist.domain.results import PriceOnDateResult


class DeterministicInterpretation:
    """Render structured analysis results using deterministic templates."""

    def interpret(
        self,
        execution: AnalysisExecutionResult,
    ) -> str:
        sections = tuple(
            self._interpret_step(step_result.result)
            for step_result in execution.step_results
        )

        return "\n\n".join(sections)

    def _interpret_step(
        self,
        result: object,
    ) -> str:
        if isinstance(result, VolatilityComparisonResult):
            return self._interpret_volatility(result)

        if isinstance(result, PriceOnDateResult):
            return self._interpret_price(result)

        if isinstance(result, PerformanceAnalysisResult):
            return self._interpret_performance(result)

        if isinstance(result, CorrelationAnalysisResult):
            return self._interpret_correlation(result)

        if isinstance(result, DrawdownComparisonResult):
            return self._interpret_drawdown(result)

        if isinstance(result, RankingResult):
            return self._interpret_ranking(result)

        raise ValueError(f"unsupported execution result: {type(result).__name__}")

    @staticmethod
    def _interpret_volatility(
        result: VolatilityComparisonResult,
    ) -> str:
        period_label = _format_period(
            result.start_date,
            result.end_date,
            result.effective_start_date,
            result.effective_end_date,
        )
        lines = [f"Historical volatility comparison {period_label}:"]

        for rank, item in enumerate(result.items, start=1):
            name = item.name or item.symbol
            lines.append(f"{rank}. {name} ({item.symbol}): {item.volatility:.2%}")

        return "\n".join(lines)

    @staticmethod
    def _interpret_price(
        result: PriceOnDateResult,
    ) -> str:
        name = result.asset.name or result.asset.symbol

        answer = (
            f"{name} ({result.asset.symbol}) was "
            f"{result.price} {result.asset.currency or ''} "
            f"on {result.effective_date}."
        )

        if result.used_previous_session:
            answer += (
                f" The requested date was {result.requested_date}, "
                "so the previous available trading session was used."
            )

        return answer

    @staticmethod
    def _interpret_performance(
        result: PerformanceAnalysisResult,
    ) -> str:
        lines = [f"Performance analysis ({result.measure.value}):"]
        for period in result.periods:
            label = (
                period.horizon.value.upper() if period.horizon else "Explicit period"
            )
            period_label = _format_period(
                period.requested_start_date,
                period.requested_end_date,
                period.effective_start_date,
                period.effective_end_date,
            )
            lines.append(f"{label}: {period_label}")
            if period.benchmark is not None:
                benchmark_name = period.benchmark.name or period.benchmark.symbol
                lines.append(
                    f"Benchmark {benchmark_name} ({period.benchmark.symbol}): "
                    f"{period.benchmark.value:.2%}"
                )
            for position, item in enumerate(period.items, start=1):
                name = item.name or item.symbol
                prefix = item.rank if item.rank is not None else position
                lines.append(f"{prefix}. {name} ({item.symbol}): {item.value:.2%}")

        return "\n".join(lines)

    @staticmethod
    def _interpret_correlation(
        result: CorrelationAnalysisResult,
    ) -> str:
        period_label = _format_period(
            result.start_date,
            result.end_date,
            result.effective_start_date,
            result.effective_end_date,
        )
        lines = [f"Historical correlation analysis {period_label}:"]

        for item in result.items:
            first_name = item.first_name or item.first_symbol
            second_name = item.second_name or item.second_symbol

            lines.append(
                f"{first_name} ({item.first_symbol}) / "
                f"{second_name} ({item.second_symbol}): "
                f"{item.correlation:.2f}"
            )

        return "\n".join(lines)

    @staticmethod
    def _interpret_drawdown(
        result: DrawdownComparisonResult,
    ) -> str:
        period_label = _format_period(
            result.start_date,
            result.end_date,
            result.effective_start_date,
            result.effective_end_date,
        )
        lines = [f"Maximum drawdown comparison {period_label}:"]

        for rank, item in enumerate(result.items, start=1):
            name = item.name or item.symbol

            line = (
                f"{rank}. {name} ({item.symbol}): "
                f"{item.maximum_drawdown:.2%} "
                f"(peak {item.peak_date}, "
                f"trough {item.trough_date}"
            )

            if item.recovery_date is not None:
                line += f", recovery {item.recovery_date}"

            line += ")"

            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def _interpret_ranking(
        result: RankingResult,
    ) -> str:
        period_label = _format_period(
            result.start_date,
            result.end_date,
            result.effective_start_date,
            result.effective_end_date,
        )
        lines = [f"Ranking by {result.metric} {period_label}:"]

        for item in result.items:
            name = item.name or item.symbol

            lines.append(f"{item.rank}. {name} ({item.symbol}): {item.value:.2%}")

        return "\n".join(lines)

    @staticmethod
    def interpret_validation(
        validation: RequestValidationResult,
    ) -> str:
        if validation.status == RequestStatus.NEEDS_CLARIFICATION:
            header = "I need clarification before running the analysis:"

        elif validation.status == RequestStatus.UNSUPPORTED:
            header = "I understand the request, but this analysis is not supported yet:"

        else:
            raise ValueError(f"unexpected validation status: {validation.status}")

        lines = [
            header,
            *(f"- {issue}" for issue in validation.issues),
        ]

        return "\n".join(lines)


def _format_period(
    requested_start: date,
    requested_end: date,
    effective_start: date | None,
    effective_end: date | None,
) -> str:
    requested = f"from {requested_start} to {requested_end}"
    if effective_start is None or effective_end is None:
        return f"requested {requested} (effective dates unavailable)"
    if (requested_start, requested_end) == (effective_start, effective_end):
        return requested
    return (
        f"requested {requested}; calculated from {effective_start} to {effective_end} "
        "(previous-session adjustment)"
    )
