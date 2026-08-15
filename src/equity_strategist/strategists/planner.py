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

    def plan(
        self,
        request: AnalysisRequest,
    ) -> AnalysisPlan:

        if request.objective == AnalysisObjective.COMPARE and set(request.metrics) == {
            AnalysisMetric.PERFORMANCE,
            AnalysisMetric.VOLATILITY,
        }:
            return AnalysisPlan(
                request=request,
                steps=(
                    PlanStep(
                        capability=Capability.COMPARE_PERFORMANCE,
                    ),
                    PlanStep(
                        capability=Capability.COMPARE_VOLATILITY,
                    ),
                ),
            )

        if request.objective == AnalysisObjective.COMPARE and request.metrics == (
            AnalysisMetric.VOLATILITY,
        ):
            return AnalysisPlan(
                request=request,
                steps=(PlanStep(capability=Capability.COMPARE_VOLATILITY),),
            )

        if request.objective == AnalysisObjective.GET and request.metrics == (
            AnalysisMetric.PRICE,
        ):
            return AnalysisPlan(
                request=request,
                steps=(PlanStep(capability=Capability.PRICE_ON_DATE),),
            )

        if request.objective == AnalysisObjective.COMPARE and request.metrics == (
            AnalysisMetric.PERFORMANCE,
        ):
            return AnalysisPlan(
                request=request,
                steps=(PlanStep(capability=Capability.COMPARE_PERFORMANCE),),
            )

        if request.objective == AnalysisObjective.ANALYZE and request.metrics == (
            AnalysisMetric.CORRELATION,
        ):
            return AnalysisPlan(
                request=request,
                steps=(PlanStep(capability=Capability.ANALYZE_CORRELATION),),
            )

        if request.objective == AnalysisObjective.COMPARE and request.metrics == (
            AnalysisMetric.DRAWDOWN,
        ):
            return AnalysisPlan(
                request=request,
                steps=(PlanStep(capability=Capability.COMPARE_DRAWDOWN),),
            )

        if request.objective == AnalysisObjective.RANK and request.metrics == (
            AnalysisMetric.PERFORMANCE,
        ):
            return AnalysisPlan(
                request=request,
                steps=(PlanStep(capability=Capability.RANK_PERFORMANCE),),
            )

        if request.objective == AnalysisObjective.RANK and request.metrics == (
            AnalysisMetric.VOLATILITY,
        ):
            return AnalysisPlan(
                request=request,
                steps=(
                    PlanStep(
                        capability=Capability.RANK_VOLATILITY,
                    ),
                ),
            )

        raise ValueError("unsupported analysis request")
