from datetime import date

from equity_strategist.domain.market_series import (
    MarketSeries,
    SeriesKind,
)


def compute_total_performance(
    price_series: MarketSeries,
) -> float:
    """Compute total simple performance over the full series."""
    _validate_price_series(price_series)

    first_price = float(price_series.values.iloc[0])
    last_price = float(price_series.values.iloc[-1])

    return last_price / first_price - 1.0


def compute_period_performance(
    price_series: MarketSeries,
    start_date: date,
    end_date: date,
) -> float:
    """Compute performance between two dates using available observations."""
    _validate_price_series(price_series)

    if start_date > end_date:
        raise ValueError("start_date must be before or equal to end_date")

    selected_values = price_series.values.loc[
        start_date.isoformat() : end_date.isoformat()
    ]

    if selected_values.empty:
        raise ValueError("no observations available over the requested period")

    if len(selected_values) < 2:
        raise ValueError("at least two observations are required")

    first_price = float(selected_values.iloc[0])
    last_price = float(selected_values.iloc[-1])

    return last_price / first_price - 1.0


def compute_annualized_performance(
    price_series: MarketSeries,
) -> float:
    """Compute annualized performance using actual elapsed calendar days."""
    _validate_price_series(price_series)

    elapsed_days = (price_series.end_date - price_series.start_date).days

    if elapsed_days <= 0:
        raise ValueError(
            "annualized performance requires observations on distinct dates"
        )

    total_performance = compute_total_performance(price_series)
    growth_factor = 1.0 + total_performance

    if growth_factor <= 0:
        raise ValueError("annualized performance requires a positive growth factor")

    elapsed_years = elapsed_days / 365.25

    return growth_factor ** (1.0 / elapsed_years) - 1.0


def compute_cumulative_performance(
    price_series: MarketSeries,
) -> MarketSeries:
    """Compute cumulative performance from the first observation."""
    _validate_price_series(price_series)

    first_price = float(price_series.values.iloc[0])
    values = price_series.values / first_price - 1.0

    metadata = dict(price_series.metadata)
    metadata.update(
        {
            "source_identifier": price_series.identifier,
            "calculation": "cumulative_performance",
        }
    )

    return MarketSeries(
        identifier=price_series.identifier,
        kind=SeriesKind.RETURN,
        values=values,
        unit="decimal",
        metadata=metadata,
    )


def _validate_price_series(
    price_series: MarketSeries,
) -> None:
    if price_series.kind != SeriesKind.PRICE:
        raise ValueError("performance calculations require a price series")

    if price_series.observation_count < 2:
        raise ValueError("at least two price observations are required")

    if (price_series.values <= 0).any():
        raise ValueError("price observations must be strictly positive")
