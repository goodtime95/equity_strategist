from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import pandas as pd


class SeriesKind(StrEnum):
    """Semantic type of a market time series."""

    PRICE = "price"
    RETURN = "return"
    RATE = "rate"
    VOLATILITY = "volatility"
    SPREAD = "spread"
    VOLUME = "volume"


@dataclass(frozen=True)
class MarketSeries:
    """A validated financial time series with business metadata."""

    identifier: str
    kind: SeriesKind
    values: pd.Series
    unit: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        clean_identifier = self.identifier.strip()
        clean_unit = self.unit.strip()

        if not clean_identifier:
            raise ValueError("identifier cannot be empty")

        if not clean_unit:
            raise ValueError("unit cannot be empty")

        values = self._normalize_values(self.values)

        object.__setattr__(self, "identifier", clean_identifier)
        object.__setattr__(self, "unit", clean_unit)
        object.__setattr__(self, "values", values)

    @staticmethod
    def _normalize_values(values: pd.Series) -> pd.Series:
        if not isinstance(values, pd.Series):
            raise TypeError("values must be a pandas Series")

        if not isinstance(values.index, pd.DatetimeIndex):
            raise TypeError("values index must be a pandas DatetimeIndex")

        if values.index.has_duplicates:
            raise ValueError("values index cannot contain duplicate dates")

        normalized = values.copy()
        normalized.index = normalized.index.tz_localize(None)
        normalized = normalized.sort_index()

        if normalized.empty:
            raise ValueError("values cannot be empty")

        if normalized.isna().any():
            raise ValueError("values cannot contain missing observations")

        if not pd.api.types.is_numeric_dtype(normalized.dtype):
            raise TypeError("values must contain numeric observations")

        normalized = normalized.astype(float)

        return normalized

    @property
    def start_date(self) -> pd.Timestamp:
        """First observation date."""

        return self.values.index[0]

    @property
    def end_date(self) -> pd.Timestamp:
        """Last observation date."""

        return self.values.index[-1]

    @property
    def observation_count(self) -> int:
        """Number of observations."""

        return len(self.values)
