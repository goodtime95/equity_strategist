from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from equity_strategist.domain.asset import Asset


@dataclass(frozen=True, slots=True)
class PriceOnDateResult:
    """Result of a price lookup for a requested date."""

    asset: Asset
    requested_date: date
    effective_date: date
    price: Decimal
    price_type: str
    used_previous_session: bool
