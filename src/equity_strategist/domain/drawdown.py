from dataclasses import dataclass

import pandas as pd

from equity_strategist.domain.market_series import MarketSeries


@dataclass(frozen=True, slots=True)
class DrawdownResult:
    """Summary of the maximum drawdown of a price series."""

    drawdown_series: MarketSeries
    maximum_drawdown: float
    peak_date: pd.Timestamp
    trough_date: pd.Timestamp
    recovery_date: pd.Timestamp | None
