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


class RankingDirection(StrEnum):
    """Direction used to order ranking results."""

    HIGHEST = "highest"
    LOWEST = "lowest"


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
    ranking_direction: RankingDirection | None = None
    top_n: int | None = None

    def __post_init__(self) -> None:
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date must be before or equal to end_date")

        if self.ranking_direction is not None and not isinstance(
            self.ranking_direction,
            RankingDirection,
        ):
            raise TypeError("ranking_direction must be a RankingDirection or None")

        if self.top_n is not None:
            if not isinstance(self.top_n, int) or isinstance(self.top_n, bool):
                raise TypeError("top_n must be an integer or None")

            if self.top_n < 1:
                raise ValueError("top_n must be greater than zero")
