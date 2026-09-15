from dataclasses import dataclass
from datetime import date

from equity_strategist.domain.analysis_request import (
    AnalysisHorizon,
    PerformanceMeasure,
    RankingDirection,
)


@dataclass(frozen=True, slots=True)
class VolatilityItem:
    """Volatility result for one asset."""

    symbol: str
    name: str | None
    volatility: float
    currency: str | None = None
    observation_count: int | None = None


@dataclass(frozen=True, slots=True)
class VolatilityComparisonResult:
    """Structured result of a multi-asset volatility comparison."""

    start_date: date
    end_date: date
    annualization_factor: int
    items: tuple[VolatilityItem, ...]
    effective_start_date: date | None = None
    effective_end_date: date | None = None
    price_field: str | None = None
    return_method: str | None = None


@dataclass(frozen=True, slots=True)
class PerformanceItem:
    """One transparent performance value for an asset."""

    symbol: str
    name: str | None
    performance: float | None = None
    value: float | None = None
    currency: str | None = None
    observation_count: int = 0
    total_performance: float | None = None
    rank: int | None = None
    asset_performance: float | None = None
    benchmark_performance: float | None = None

    def __post_init__(self) -> None:
        if self.value is None and self.performance is None:
            raise ValueError("performance item requires a value")
        value = self.performance if self.value is None else self.value
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "performance", value)


@dataclass(frozen=True, slots=True)
class PerformanceBenchmark:
    """Benchmark calculation retained alongside asset results."""

    symbol: str
    name: str | None
    currency: str | None
    observation_count: int
    total_performance: float
    value: float


@dataclass(frozen=True, slots=True)
class PerformancePeriodResult:
    """Performance results for one explicit or standard period."""

    horizon: AnalysisHorizon | None
    requested_start_date: date
    requested_end_date: date
    effective_start_date: date
    effective_end_date: date
    items: tuple[PerformanceItem, ...]
    benchmark: PerformanceBenchmark | None = None


@dataclass(frozen=True, slots=True)
class PerformanceAnalysisResult:
    """Single result contract for explicit and multi-horizon performance."""

    measure: PerformanceMeasure
    periods: tuple[PerformancePeriodResult, ...]
    price_field: str = "adjusted_close"
    return_method: str = "simple"
    annualization_factor: float | None = None
    ranking_direction: RankingDirection | None = None
    top_n: int | None = None

    @property
    def items(self) -> tuple[PerformanceItem, ...]:
        """Return items for backward-compatible single-period callers."""
        return self.periods[0].items

    @property
    def start_date(self) -> date:
        return self.periods[0].requested_start_date

    @property
    def end_date(self) -> date:
        return self.periods[0].requested_end_date


def PerformanceComparisonResult(
    start_date: date,
    end_date: date,
    items: tuple[PerformanceItem, ...],
) -> PerformanceAnalysisResult:
    """Compatibility constructor for the former single-period result."""
    normalized_items = tuple(
        PerformanceItem(
            symbol=item.symbol,
            name=item.name,
            performance=item.value,
            value=item.value,
            currency=item.currency,
            observation_count=item.observation_count,
            total_performance=(
                item.value if item.total_performance is None else item.total_performance
            ),
            rank=item.rank,
            asset_performance=item.asset_performance,
            benchmark_performance=item.benchmark_performance,
        )
        for item in items
    )
    return PerformanceAnalysisResult(
        measure=PerformanceMeasure.TOTAL,
        periods=(
            PerformancePeriodResult(
                horizon=None,
                requested_start_date=start_date,
                requested_end_date=end_date,
                effective_start_date=start_date,
                effective_end_date=end_date,
                items=normalized_items,
            ),
        ),
    )


@dataclass(frozen=True, slots=True)
class CorrelationItem:
    """Correlation result for one pair of assets."""

    first_symbol: str
    first_name: str | None
    second_symbol: str
    second_name: str | None
    correlation: float
    observation_count: int | None = None
    first_currency: str | None = None
    second_currency: str | None = None


@dataclass(frozen=True, slots=True)
class CorrelationAnalysisResult:
    """Structured multi-asset correlation analysis."""

    start_date: date
    end_date: date
    items: tuple[CorrelationItem, ...]
    effective_start_date: date | None = None
    effective_end_date: date | None = None
    price_field: str | None = None
    return_method: str | None = None


@dataclass(frozen=True, slots=True)
class DrawdownItem:
    """Maximum drawdown result for one asset."""

    symbol: str
    name: str | None
    maximum_drawdown: float
    peak_date: date
    trough_date: date
    recovery_date: date | None
    currency: str | None = None
    observation_count: int | None = None


@dataclass(frozen=True, slots=True)
class DrawdownComparisonResult:
    """Structured multi-asset drawdown comparison."""

    start_date: date
    end_date: date
    items: tuple[DrawdownItem, ...]
    effective_start_date: date | None = None
    effective_end_date: date | None = None
    price_field: str | None = None


@dataclass(frozen=True, slots=True)
class RankingItem:
    """Ranked metric result for one asset."""

    rank: int
    symbol: str
    name: str | None
    value: float
    currency: str | None = None
    observation_count: int | None = None


@dataclass(frozen=True, slots=True)
class RankingResult:
    """Structured ranking across several assets."""

    metric: str
    start_date: date
    end_date: date
    items: tuple[RankingItem, ...]
    effective_start_date: date | None = None
    effective_end_date: date | None = None
    price_field: str | None = None
    return_method: str | None = None
    annualization_factor: int | None = None
