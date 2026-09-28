"""Typed failures assigned only at boundaries that know the cause."""

from enum import StrEnum

from equity_strategist.domain.universe import Universe


class ErrorCategory(StrEnum):
    INTERNAL_ERROR = "internal_error"
    PROVIDER_FAILURE = "provider_failure"
    INSUFFICIENT_DATA = "insufficient_data"
    AMBIGUOUS_ASSET = "ambiguous_asset"
    ASSET_NOT_FOUND = "asset_not_found"


class ProviderFailure(RuntimeError):
    """An external provider call failed."""


class InsufficientDataError(ValueError):
    """Available observations cannot support the requested calculation."""


class UnknownUniverseError(ValueError):
    """The local catalog does not provide the requested constituent universe."""


class AmbiguousUniverseError(ValueError):
    """Multiple registered universes match the supplied reference."""

    def __init__(self, query: str, candidates: tuple[Universe, ...]) -> None:
        super().__init__(f"ambiguous universe: {query}")
        self.candidates = candidates
