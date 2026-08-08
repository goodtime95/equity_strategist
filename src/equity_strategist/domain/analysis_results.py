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
