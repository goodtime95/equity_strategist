"""Typed failures assigned only at boundaries that know the cause."""

from enum import StrEnum


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
