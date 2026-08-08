from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class AnalysisIntent(StrEnum):
    """Supported user analysis intents."""

    COMPARE_VOLATILITY = "compare_volatility"
    PRICE_ON_DATE = "price_on_date"


@dataclass(frozen=True, slots=True)
class AnalysisRequest:
    """Structured representation of a user analysis request."""

    intent: AnalysisIntent
    assets: tuple[str, ...]
    start_date: date | None = None
    end_date: date | None = None
    target_date: date | None = None

    def __post_init__(self) -> None:
        if not self.assets:
            raise ValueError("at least one asset is required")

        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date must be before or equal to end_date")
