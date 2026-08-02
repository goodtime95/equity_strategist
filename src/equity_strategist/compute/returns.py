from enum import StrEnum

import numpy as np
import pandas as pd

from equity_strategist.domain.market_series import (
    MarketSeries,
    SeriesKind,
)


class ReturnMethod(StrEnum):
    """Supported methods for computing financial returns."""

    SIMPLE = "simple"
    LOG = "log"


def compute_returns(
    price_series: MarketSeries,
    method: ReturnMethod = ReturnMethod.SIMPLE,
) -> MarketSeries:
    """Compute returns from a market price series."""
    if price_series.kind != SeriesKind.PRICE:
        raise ValueError("compute_returns requires a price series")

    if price_series.observation_count < 2:
        raise ValueError("at least two price observations are required")

    if (price_series.values <= 0).any():
        raise ValueError("price observations must be strictly positive")

    if method == ReturnMethod.SIMPLE:
        values = price_series.values.pct_change().dropna()
    elif method == ReturnMethod.LOG:
        values = np.log(price_series.values / price_series.values.shift(1)).dropna()
    else:
        raise ValueError(f"unsupported return method: {method}")

    values = pd.Series(
        values,
        index=values.index,
        name=f"{price_series.identifier}_{method.value}_returns",
        dtype=float,
    )

    metadata = dict(price_series.metadata)
    metadata.update(
        {
            "source_identifier": price_series.identifier,
            "return_method": method.value,
        }
    )

    return MarketSeries(
        identifier=price_series.identifier,
        kind=SeriesKind.RETURN,
        values=values,
        unit="decimal",
        metadata=metadata,
    )
