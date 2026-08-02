import pandas as pd

from equity_strategist.domain.asset import Asset
from equity_strategist.domain.market_series import (
    MarketSeries,
    SeriesKind,
)
from equity_strategist.domain.observations import (
    DailyPriceObservation,
)


def extract_price_series(
    asset: Asset,
    observations: list[DailyPriceObservation],
    use_adjusted_close: bool = True,
) -> MarketSeries:
    """Extract a price time series from daily price observations."""
    if not observations:
        raise ValueError("observations cannot be empty")

    field = "adjusted_close" if use_adjusted_close else "close"
    values_by_date: dict[pd.Timestamp, float] = {}

    for observation in observations:
        if observation.asset.symbol != asset.symbol:
            raise ValueError("all observations must belong to the requested asset")

        if use_adjusted_close:
            if observation.adjusted_close is None:
                raise ValueError(
                    "adjusted close is missing for at least one observation"
                )

            value = observation.adjusted_close
        else:
            value = observation.close

        observation_date = pd.Timestamp(observation.date)

        if observation_date in values_by_date:
            raise ValueError(
                f"duplicate price observation for {observation_date.date()}"
            )

        values_by_date[observation_date] = float(value)

    values = pd.Series(
        values_by_date,
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
            "source_type": "daily_price_observations",
        },
    )
