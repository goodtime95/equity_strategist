from equity_strategist.domain.analysis_plan import (
    AnalysisPlan,
    Capability,
    PlanStep,
)
from equity_strategist.domain.analysis_request import (
    AnalysisIntent,
    AnalysisRequest,
)


class EquityPlanner:
    """Build deterministic execution plans from structured requests."""

    def plan(
        self,
        request: AnalysisRequest,
    ) -> AnalysisPlan:
        if request.intent == AnalysisIntent.COMPARE_VOLATILITY:
            return AnalysisPlan(
                request=request,
                steps=(PlanStep(capability=Capability.COMPARE_VOLATILITY),),
            )

        if request.intent == AnalysisIntent.PRICE_ON_DATE:
            return AnalysisPlan(
                request=request,
                steps=(PlanStep(capability=Capability.PRICE_ON_DATE),),
            )

        raise ValueError(f"unsupported analysis intent: {request.intent}")
