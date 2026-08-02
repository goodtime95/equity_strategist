import math

from equity_strategist.domain.market_series import (
    MarketSeries,
    SeriesKind,
)


def compute_volatility(
    return_series: MarketSeries,
    annualization_factor: int = 252,
    ddof: int = 1,
) -> float:
    """Compute annualized historical volatility from returns."""
    _validate_return_series(
        return_series=return_series,
        annualization_factor=annualization_factor,
        ddof=ddof,
    )

    periodic_volatility = float(return_series.values.std(ddof=ddof))

    return periodic_volatility * math.sqrt(annualization_factor)


def compute_rolling_volatility(
    return_series: MarketSeries,
    window: int,
    annualization_factor: int = 252,
    ddof: int = 1,
) -> MarketSeries:
    """Compute annualized rolling historical volatility."""
    _validate_return_series(
        return_series=return_series,
        annualization_factor=annualization_factor,
        ddof=ddof,
    )

    if window <= ddof:
        raise ValueError("window must be greater than ddof")

    if window > return_series.observation_count:
        raise ValueError("window cannot exceed the number of observations")

    values = return_series.values.rolling(window=window).std(
        ddof=ddof
    ).dropna() * math.sqrt(annualization_factor)

    metadata = dict(return_series.metadata)
    metadata.update(
        {
            "source_identifier": return_series.identifier,
            "calculation": "rolling_volatility",
            "window": window,
            "annualization_factor": annualization_factor,
            "ddof": ddof,
        }
    )

    return MarketSeries(
        identifier=return_series.identifier,
        kind=SeriesKind.VOLATILITY,
        values=values,
        unit="decimal",
        metadata=metadata,
    )


def _validate_return_series(
    return_series: MarketSeries,
    annualization_factor: int,
    ddof: int,
) -> None:
    if return_series.kind != SeriesKind.RETURN:
        raise ValueError("volatility calculations require a return series")

    if return_series.observation_count < 2:
        raise ValueError("at least two return observations are required")

    if annualization_factor <= 0:
        raise ValueError("annualization_factor must be strictly positive")

    if ddof < 0:
        raise ValueError("ddof cannot be negative")

    if ddof >= return_series.observation_count:
        raise ValueError("ddof must be smaller than the number of observations")
