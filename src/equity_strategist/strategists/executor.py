from equity_strategist.domain.analysis_execution import (
    AnalysisExecutionResult,
    StepExecutionResult,
)
from equity_strategist.domain.analysis_plan import (
    AnalysisPlan,
    Capability,
)
from equity_strategist.services.market_queries import (
    MarketQueryService,
)
from equity_strategist.services.volatility_analysis import (
    VolatilityAnalysisService,
)


class EquityExecutor:
    """Execute deterministic equity analysis plans."""

    def __init__(
        self,
        volatility_analysis_service: VolatilityAnalysisService,
        market_query_service: MarketQueryService,
    ) -> None:
        self.volatility_analysis_service = volatility_analysis_service
        self.market_query_service = market_query_service

    def execute(
        self,
        plan: AnalysisPlan,
    ) -> AnalysisExecutionResult:
        """Execute all steps of an analysis plan."""
        step_results: list[StepExecutionResult] = []

        for step in plan.steps:
            result = self._execute_step(
                capability=step.capability,
                plan=plan,
            )

            step_results.append(
                StepExecutionResult(
                    capability=step.capability,
                    result=result,
                )
            )

        return AnalysisExecutionResult(
            plan=plan,
            step_results=tuple(step_results),
        )

    def _execute_step(
        self,
        capability: Capability,
        plan: AnalysisPlan,
    ) -> object:
        request = plan.request

        if capability == Capability.COMPARE_VOLATILITY:
            if request.start_date is None:
                raise ValueError("COMPARE_VOLATILITY requires start_date")

            if request.end_date is None:
                raise ValueError("COMPARE_VOLATILITY requires end_date")

            return self.volatility_analysis_service.compare(
                asset_queries=list(request.assets),
                start_date=request.start_date,
                end_date=request.end_date,
            )

        if capability == Capability.PRICE_ON_DATE:
            if len(request.assets) != 1:
                raise ValueError("PRICE_ON_DATE requires exactly one asset")

            if request.target_date is None:
                raise ValueError("PRICE_ON_DATE requires target_date")

            return self.market_query_service.get_price_on_date(
                asset_query=request.assets[0],
                target_date=request.target_date,
            )

        raise ValueError(f"unsupported capability: {capability}")
