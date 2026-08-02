from equity_strategist.domain.market_series import (
    MarketSeries,
    SeriesKind,
)


def compute_correlation(
    first_series: MarketSeries,
    second_series: MarketSeries,
    method: str = "pearson",
    min_observations: int = 2,
) -> float:
    """Compute correlation using observations available on common dates."""
    aligned_first, aligned_second = _align_return_series(
        first_series=first_series,
        second_series=second_series,
        min_observations=min_observations,
    )

    correlation = aligned_first.corr(
        aligned_second,
        method=method,
    )

    if correlation != correlation:
        raise ValueError("correlation is undefined for the aligned observations")

    return float(correlation)


def compute_rolling_correlation(
    first_series: MarketSeries,
    second_series: MarketSeries,
    window: int,
    min_observations: int | None = None,
) -> MarketSeries:
    """Compute rolling Pearson correlation on common observation dates."""
    if window < 2:
        raise ValueError("window must be at least 2")

    required_observations = window if min_observations is None else min_observations

    if required_observations < 2:
        raise ValueError("min_observations must be at least 2")

    if required_observations > window:
        raise ValueError("min_observations cannot exceed window")

    aligned_first, aligned_second = _align_return_series(
        first_series=first_series,
        second_series=second_series,
        min_observations=2,
    )

    if window > len(aligned_first):
        raise ValueError("window cannot exceed the number of overlapping observations")

    values = (
        aligned_first.rolling(
            window=window,
            min_periods=required_observations,
        )
        .corr(aligned_second)
        .dropna()
    )

    if values.empty:
        raise ValueError("rolling correlation produced no valid observations")

    return MarketSeries(
        identifier=(f"{first_series.identifier}_{second_series.identifier}"),
        kind=SeriesKind.CORRELATION,
        values=values,
        unit="decimal",
        metadata={
            "first_identifier": first_series.identifier,
            "second_identifier": second_series.identifier,
            "calculation": "rolling_correlation",
            "window": window,
            "min_observations": required_observations,
            "method": "pearson",
        },
    )


def _align_return_series(
    first_series: MarketSeries,
    second_series: MarketSeries,
    min_observations: int,
):
    _validate_return_series(first_series)
    _validate_return_series(second_series)

    if min_observations < 2:
        raise ValueError("min_observations must be at least 2")

    common_index = first_series.values.index.intersection(second_series.values.index)

    if len(common_index) < min_observations:
        raise ValueError("insufficient overlapping observations")

    first_values = first_series.values.loc[common_index]
    second_values = second_series.values.loc[common_index]

    return first_values, second_values


def _validate_return_series(series: MarketSeries) -> None:
    if series.kind != SeriesKind.RETURN:
        raise ValueError("correlation calculations require return series")
