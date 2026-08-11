from typing import Protocol

from equity_strategist.domain.universe_constituent import (
    UniverseConstituent,
)


class UniverseProvider(Protocol):
    """Provider able to return constituents of a dynamic universe."""

    def get_constituents(
        self,
        provider_identifier: str,
    ) -> tuple[UniverseConstituent, ...]:
        """Return structured constituent references."""
        ...
