from dataclasses import dataclass

from equity_strategist.domain.market_series import MarketSeries


@dataclass(frozen=True, slots=True)
class MarketDataset:
    """A coherent collection of market series."""

    series_by_symbol: dict[str, MarketSeries]
    universe: str | None = None

    def __post_init__(self) -> None:
        if not self.series_by_symbol:
            raise ValueError("market dataset cannot be empty")

        for symbol, series in self.series_by_symbol.items():
            if symbol != series.identifier:
                raise ValueError("dataset key must match series identifier")

    @property
    def symbols(self) -> tuple[str, ...]:
        """Return dataset symbols."""
        return tuple(self.series_by_symbol)

    @property
    def size(self) -> int:
        """Return number of series."""
        return len(self.series_by_symbol)

    def get(self, symbol: str) -> MarketSeries:
        """Return a market series by symbol."""
        try:
            return self.series_by_symbol[symbol]
        except KeyError as exc:
            raise KeyError(f"symbol not found in dataset: {symbol}") from exc
