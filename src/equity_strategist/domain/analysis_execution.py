from dataclasses import dataclass

from equity_strategist.domain.analysis_plan import (
    AnalysisPlan,
    Capability,
)


@dataclass(frozen=True, slots=True)
class StepExecutionResult:
    """Result produced by one executed plan step."""

    capability: Capability
    result: object


@dataclass(frozen=True, slots=True)
class AnalysisExecutionResult:
    """Results produced by executing an analysis plan."""

    plan: AnalysisPlan
    step_results: tuple[StepExecutionResult, ...]

    def __post_init__(self) -> None:
        if not self.step_results:
            raise ValueError("analysis execution result cannot be empty")
