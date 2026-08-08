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

        raise ValueError("unsupported analysis request")
