import pandas as pd

from equity_strategist.domain.market_series import (
    MarketSeries,
    SeriesKind,
)
from equity_strategist.domain.models import Asset, PriceBar


def build_price_series(
    asset: Asset,
    prices: list[PriceBar],
    use_adjusted_close: bool = True,
) -> MarketSeries:
    """Build a validated price series from daily price bars."""
    if not prices:
        raise ValueError("prices cannot be empty")

    field = "adjusted_close" if use_adjusted_close else "close"
    observations: dict[pd.Timestamp, float] = {}

    for price_bar in prices:
        if price_bar.asset.symbol != asset.symbol:
            raise ValueError("all price bars must belong to the requested asset")

        if use_adjusted_close:
            if price_bar.adjusted_close is None:
                raise ValueError(
                    "adjusted close is missing for at least one observation"
                )

            value = price_bar.adjusted_close
        else:
            value = price_bar.close

        observation_date = pd.Timestamp(price_bar.date)

        if observation_date in observations:
            raise ValueError(
                f"duplicate price observation for {observation_date.date()}"
            )

        observations[observation_date] = float(value)

    values = pd.Series(
        observations,
        name=asset.symbol,
        dtype=float,
    )

    return MarketSeries(
        identifier=asset.symbol,
        kind=SeriesKind.PRICE,
        values=values,
        unit=asset.currency or "unknown",
        metadata={
            "asset": asset,
            "field": field,
            "source_type": "daily_price_bars",
        },
    )
