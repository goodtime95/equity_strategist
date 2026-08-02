from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Asset:
    """A financial asset identified independently of any data provider."""

    symbol: str
    name: str | None = None
    exchange: str | None = None
    currency: str | None = None
