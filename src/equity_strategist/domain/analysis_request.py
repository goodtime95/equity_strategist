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


class PerformanceMeasure(StrEnum):
    """Deterministic performance methodology requested by the user."""

    TOTAL = "total"
    ANNUALIZED = "annualized"
    RELATIVE = "relative"
    EXCESS_RETURN = "excess_return"


class AnalysisHorizon(StrEnum):
    """Supported calendar horizons for performance analysis."""

    ONE_MONTH = "1m"
    THREE_MONTHS = "3m"
    SIX_MONTHS = "6m"
    YEAR_TO_DATE = "ytd"
    ONE_YEAR = "1y"
    THREE_YEARS = "3y"


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
    performance_measure: PerformanceMeasure = PerformanceMeasure.TOTAL
    horizons: tuple[AnalysisHorizon, ...] = ()

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

        if not isinstance(self.performance_measure, PerformanceMeasure):
            raise TypeError("performance_measure must be a PerformanceMeasure")

        if any(not isinstance(horizon, AnalysisHorizon) for horizon in self.horizons):
            raise TypeError("horizons must contain only AnalysisHorizon values")

        if len(self.horizons) != len(set(self.horizons)):
            raise ValueError("horizons cannot contain duplicates")
