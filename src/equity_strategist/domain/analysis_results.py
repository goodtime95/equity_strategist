from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class VolatilityItem:
    """Volatility result for one asset."""

    symbol: str
    name: str | None
    volatility: float


@dataclass(frozen=True, slots=True)
class VolatilityComparisonResult:
    """Structured result of a multi-asset volatility comparison."""

    start_date: date
    end_date: date
    annualization_factor: int
    items: tuple[VolatilityItem, ...]


@dataclass(frozen=True, slots=True)
class PerformanceItem:
    """Performance result for one asset."""

    symbol: str
    name: str | None
    performance: float


@dataclass(frozen=True, slots=True)
class PerformanceComparisonResult:
    """Structured multi-asset performance comparison."""

    start_date: date
    end_date: date
    items: tuple[PerformanceItem, ...]


@dataclass(frozen=True, slots=True)
class CorrelationItem:
    """Correlation result for one pair of assets."""

    first_symbol: str
    first_name: str | None
    second_symbol: str
    second_name: str | None
    correlation: float


@dataclass(frozen=True, slots=True)
class CorrelationAnalysisResult:
    """Structured multi-asset correlation analysis."""

    start_date: date
    end_date: date
    items: tuple[CorrelationItem, ...]


@dataclass(frozen=True, slots=True)
class DrawdownItem:
    """Maximum drawdown result for one asset."""

    symbol: str
    name: str | None
    maximum_drawdown: float
    peak_date: date
    trough_date: date
    recovery_date: date | None


@dataclass(frozen=True, slots=True)
class DrawdownComparisonResult:
    """Structured multi-asset drawdown comparison."""

    start_date: date
    end_date: date
    items: tuple[DrawdownItem, ...]


@dataclass(frozen=True, slots=True)
class RankingItem:
    """Ranked metric result for one asset."""

    rank: int
    symbol: str
    name: str | None
    value: float


@dataclass(frozen=True, slots=True)
class RankingResult:
    """Structured ranking across several assets."""

    metric: str
    start_date: date
    end_date: date
    items: tuple[RankingItem, ...]
