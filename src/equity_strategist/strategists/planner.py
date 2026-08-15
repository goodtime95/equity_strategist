from equity_strategist.domain.analysis_plan import (
    AnalysisPlan,
    Capability,
    PlanStep,
)
from equity_strategist.domain.analysis_request import (
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
)


class EquityPlanner:
    """Build deterministic execution plans from structured requests."""

    CAPABILITY_MAP = {
        (
            AnalysisObjective.COMPARE,
            AnalysisMetric.PERFORMANCE,
        ): Capability.COMPARE_PERFORMANCE,
        (
            AnalysisObjective.COMPARE,
            AnalysisMetric.VOLATILITY,
        ): Capability.COMPARE_VOLATILITY,
        (
            AnalysisObjective.COMPARE,
            AnalysisMetric.DRAWDOWN,
        ): Capability.COMPARE_DRAWDOWN,
        (
            AnalysisObjective.GET,
            AnalysisMetric.PRICE,
        ): Capability.PRICE_ON_DATE,
        (
            AnalysisObjective.ANALYZE,
            AnalysisMetric.CORRELATION,
        ): Capability.ANALYZE_CORRELATION,
        (
            AnalysisObjective.RANK,
            AnalysisMetric.PERFORMANCE,
        ): Capability.RANK_PERFORMANCE,
        (
            AnalysisObjective.RANK,
            AnalysisMetric.VOLATILITY,
        ): Capability.RANK_VOLATILITY,
    }

    def plan(
        self,
        request: AnalysisRequest,
    ) -> AnalysisPlan:
        steps: list[PlanStep] = []

        for metric in request.metrics:
            capability = self.CAPABILITY_MAP.get(
                (
                    request.objective,
                    metric,
                )
            )

            if capability is None:
                raise ValueError(
                    "unsupported analysis request: "
                    f"{request.objective.value} + "
                    f"{metric.value}"
                )

            steps.append(
                PlanStep(
                    capability=capability,
                )
            )

        return AnalysisPlan(
            request=request,
            steps=tuple(steps),
        )
