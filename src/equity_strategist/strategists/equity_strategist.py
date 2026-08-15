from equity_strategist.domain.analysis_execution import (
    AnalysisExecutionResult,
)
from equity_strategist.domain.analysis_request import (
    AnalysisRequest,
)
from equity_strategist.domain.analysis_results import (
    CorrelationAnalysisResult,
    DrawdownComparisonResult,
    PerformanceComparisonResult,
    RankingResult,
    VolatilityComparisonResult,
)
from equity_strategist.domain.results import PriceOnDateResult
from equity_strategist.strategists.executor import EquityExecutor
from equity_strategist.strategists.planner import EquityPlanner
from equity_strategist.understanding.rule_based import (
    RuleBasedUnderstanding,
)


class EquityStrategist:
    """Coordinate understanding, planning, execution and interpretation."""

    def __init__(
        self,
        understanding: RuleBasedUnderstanding,
        planner: EquityPlanner,
        executor: EquityExecutor,
    ) -> None:
        self.understanding = understanding
        self.planner = planner
        self.executor = executor

    def answer(
        self,
        question: str,
    ) -> str:
        """Answer a natural-language equity question."""
        request = self.understand(question)
        plan = self.planner.plan(request)
        execution = self.executor.execute(plan)

        return self.interpret(execution)

    def answer_request(
        self,
        request: AnalysisRequest,
    ) -> str:
        """Execute a structured request and return a readable answer."""
        plan = self.planner.plan(request)
        execution = self.executor.execute(plan)

        return self.interpret(execution)

    def understand(
        self,
        question: str,
    ) -> AnalysisRequest:
        """Convert natural language into a structured request."""
        return self.understanding.understand(question)

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
        """Convert one structured result into readable text."""

        if isinstance(result, VolatilityComparisonResult):
            return self._interpret_volatility(result)

        if isinstance(result, PriceOnDateResult):
            return self._interpret_price(result)

        if isinstance(result, PerformanceComparisonResult):
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
        lines = [
            (
                "Historical volatility comparison "
                f"from {result.start_date} to {result.end_date}:"
            )
        ]

        for rank, item in enumerate(
            result.items,
            start=1,
        ):
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
        result: PerformanceComparisonResult,
    ) -> str:
        lines = [
            (
                "Historical performance comparison "
                f"from {result.start_date} to {result.end_date}:"
            )
        ]

        for rank, item in enumerate(
            result.items,
            start=1,
        ):
            name = item.name or item.symbol

            lines.append(f"{rank}. {name} ({item.symbol}): {item.performance:.2%}")

        return "\n".join(lines)

    @staticmethod
    def _interpret_correlation(
        result: CorrelationAnalysisResult,
    ) -> str:
        lines = [
            (
                "Historical correlation analysis "
                f"from {result.start_date} to {result.end_date}:"
            )
        ]

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
        lines = [
            (
                "Maximum drawdown comparison "
                f"from {result.start_date} to {result.end_date}:"
            )
        ]

        for rank, item in enumerate(
            result.items,
            start=1,
        ):
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
        lines = [
            (
                f"Ranking by {result.metric} "
                f"from {result.start_date} to {result.end_date}:"
            )
        ]

        for item in result.items:
            name = item.name or item.symbol

            lines.append(f"{item.rank}. {name} ({item.symbol}): {item.value:.2%}")

        return "\n".join(lines)
