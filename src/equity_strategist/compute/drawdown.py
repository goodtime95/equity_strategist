import pandas as pd

from equity_strategist.domain.drawdown import DrawdownResult
from equity_strategist.domain.market_series import (
    MarketSeries,
    SeriesKind,
)


def compute_drawdown_series(
    price_series: MarketSeries,
) -> MarketSeries:
    """Compute drawdown from the running historical peak."""
    _validate_price_series(price_series)

    running_peak = price_series.values.cummax()
    values = price_series.values / running_peak - 1.0

    metadata = dict(price_series.metadata)
    metadata.update(
        {
            "source_identifier": price_series.identifier,
            "calculation": "drawdown",
        }
    )

    return MarketSeries(
        identifier=price_series.identifier,
        kind=SeriesKind.DRAWDOWN,
        values=values,
        unit="decimal",
        metadata=metadata,
    )


def compute_maximum_drawdown(
    price_series: MarketSeries,
) -> DrawdownResult:
    """Compute maximum drawdown and its main dates."""
    drawdown_series = compute_drawdown_series(price_series)

    trough_date = drawdown_series.values.idxmin()
    maximum_drawdown = float(drawdown_series.values.loc[trough_date])

    prices_until_trough = price_series.values.loc[:trough_date]
    peak_date = prices_until_trough.idxmax()
    peak_value = float(price_series.values.loc[peak_date])

    prices_after_trough = price_series.values.loc[trough_date:]

    recovered_prices = prices_after_trough[prices_after_trough >= peak_value]

    recovery_date: pd.Timestamp | None

    if recovered_prices.empty:
        recovery_date = None
    else:
        recovery_date = recovered_prices.index[0]

    return DrawdownResult(
        drawdown_series=drawdown_series,
        maximum_drawdown=maximum_drawdown,
        peak_date=peak_date,
        trough_date=trough_date,
        recovery_date=recovery_date,
    )


def _validate_price_series(
    price_series: MarketSeries,
) -> None:
    if price_series.kind != SeriesKind.PRICE:
        raise ValueError("drawdown calculations require a price series")

    if price_series.observation_count < 2:
        raise ValueError("at least two price observations are required")

    if (price_series.values <= 0).any():
        raise ValueError("price observations must be strictly positive")
