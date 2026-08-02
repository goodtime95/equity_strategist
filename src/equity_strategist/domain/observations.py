from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from equity_strategist.domain.asset import Asset


@dataclass(frozen=True, slots=True)
class DailyPriceObservation:
    """Daily OHLCV market observation for one asset."""

    asset: Asset
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int | None = None
    adjusted_close: Decimal | None = None
