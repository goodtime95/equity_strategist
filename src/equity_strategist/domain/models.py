from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Asset:
    """A financial asset identified by a provider-independent symbol."""

    symbol: str
    name: str | None = None
    exchange: str | None = None
    currency: str | None = None


@dataclass(frozen=True, slots=True)
class PriceBar:
    """Daily OHLCV market data for one asset."""

    asset: Asset
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int | None = None
    adjusted_close: Decimal | None = None


@dataclass(frozen=True, slots=True)
class PriceOnDateResult:
    """Result of a price lookup for a requested date."""

    asset: Asset
    requested_date: date
    effective_date: date
    price: Decimal
    price_type: str
    used_previous_session: bool
