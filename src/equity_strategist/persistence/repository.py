from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from equity_strategist.application.run_snapshot import RunSnapshot


class StorageUnavailable(RuntimeError):
    pass


class UnknownRun(LookupError):
    pass


@dataclass(frozen=True)
class Feedback:
    feedback_id: UUID
    request_id: UUID
    useful: bool
    comment: str | None
    created_at: datetime


class RunRepository(Protocol):
    def save_run(self, snapshot: RunSnapshot) -> None: ...
    def save_feedback(self, feedback: Feedback) -> None: ...
    def delete_request(self, request_id: UUID) -> int: ...
    def delete_thread(self, thread_id: str) -> int:
        """Delete by the external thread ID, applying the canonical storage identity."""
        ...

    def cleanup(self, before: datetime) -> int: ...
    def close(self) -> None: ...


class NoOpRunRepository:
    def save_run(self, snapshot: RunSnapshot) -> None:
        pass

    def save_feedback(self, feedback: Feedback) -> None:
        raise StorageUnavailable("Feedback storage unavailable")

    def delete_request(self, request_id: UUID) -> int:
        return 0

    def delete_thread(self, thread_id: str) -> int:
        return 0

    def cleanup(self, before: datetime) -> int:
        return 0

    def close(self) -> None:
        pass
