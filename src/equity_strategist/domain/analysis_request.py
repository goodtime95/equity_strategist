from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class AnalysisObjective(StrEnum):
    """High-level objective of the user request."""

    GET = "get"
    COMPARE = "compare"
    RANK = "rank"
    ANALYZE = "analyze"


class AnalysisMetric(StrEnum):
    """Financial metrics that may be requested."""

    PRICE = "price"
    PERFORMANCE = "performance"
    VOLATILITY = "volatility"
    CORRELATION = "correlation"
    DRAWDOWN = "drawdown"


@dataclass(frozen=True, slots=True)
class AnalysisRequest:
    """Structured representation of a user analysis request."""

    objective: AnalysisObjective
    metrics: tuple[AnalysisMetric, ...] = ()

    assets: tuple[str, ...] = ()
    universe: str | None = None

    start_date: date | None = None
    end_date: date | None = None
    target_date: date | None = None
    market_period: str | None = None

    benchmark: str | None = None

    constraints: tuple[str, ...] = ()
    user_context: str | None = None
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.assets and self.universe is None:
            raise ValueError("at least one asset or universe is required")

        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date must be before or equal to end_date")
