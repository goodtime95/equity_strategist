from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UniverseConstituent:
    """Provider-independent reference to an index constituent."""

    name: str
    isin: str | None = None
    exchange: str | None = None
    provider_symbol: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("constituent name cannot be empty")
