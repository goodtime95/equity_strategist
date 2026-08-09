from dataclasses import dataclass
from enum import StrEnum

from equity_strategist.domain.analysis_request import AnalysisRequest


class Capability(StrEnum):
    """Deterministic capabilities available to the strategist."""

    COMPARE_VOLATILITY = "compare_volatility"
    PRICE_ON_DATE = "price_on_date"
    COMPARE_PERFORMANCE = "compare_performance"
    ANALYZE_CORRELATION = "analyze_correlation"


@dataclass(frozen=True, slots=True)
class PlanStep:
    """One deterministic capability to execute."""

    capability: Capability


@dataclass(frozen=True, slots=True)
class AnalysisPlan:
    """Execution plan generated from an analysis request."""

    request: AnalysisRequest
    steps: tuple[PlanStep, ...]

    def __post_init__(self) -> None:
        if not self.steps:
            raise ValueError("analysis plan cannot be empty")
