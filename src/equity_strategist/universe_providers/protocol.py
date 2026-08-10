from typing import Protocol


class UniverseProvider(Protocol):
    """Provider able to return constituents of a dynamic universe."""

    def get_constituents(
        self,
        provider_identifier: str,
    ) -> tuple[str, ...]:
        """Return asset queries for a dynamic universe."""
        ...
