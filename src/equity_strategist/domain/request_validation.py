from dataclasses import dataclass
from enum import StrEnum


class RequestStatus(StrEnum):
    """Validation status of a structured analysis request."""

    READY = "ready"
    NEEDS_CLARIFICATION = "needs_clarification"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class RequestValidationResult:
    """Result of validating an analysis request."""

    status: RequestStatus
    issues: tuple[str, ...] = ()

    @property
    def is_ready(self) -> bool:
        return self.status == RequestStatus.READY
