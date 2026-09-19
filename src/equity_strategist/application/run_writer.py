"""Bound waiting on one run write, without queuing work or spawning replacements."""

from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from threading import Event, Lock, Thread
from time import monotonic

from equity_strategist.application.run_snapshot import RunSnapshot
from equity_strategist.persistence.repository import NoOpRunRepository, RunRepository


class WriteOutcome(StrEnum):
    STORED = "stored"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    BUSY = "busy"
    CLOSED = "closed"


@dataclass
class _Attempt:
    done: Event = field(default_factory=Event)
    outcome: WriteOutcome = WriteOutcome.FAILED


class BoundedRunWriter:
    """At most one save_run operation may be active per application coordinator.

    A timeout stops waiting, not the driver operation: its commit is uncertain.
    Until that operation exits, subsequent snapshots are dropped, never queued.
    Daemon threads are intentional: an unresponsive driver cannot hold process
    shutdown hostage. Normal/deferred shutdown closes the repository exactly once.
    """

    def __init__(self, repository: RunRepository, timeout_seconds: float = 2.0) -> None:
        if not isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("persistence timeout must be finite and positive")
        self.repository = repository
        self.timeout_seconds = timeout_seconds
        self._lock = Lock()
        self._worker: Thread | None = None
        self._saving = False
        self._closed = False
        self._close_started = False

    def write(self, snapshot: RunSnapshot) -> WriteOutcome:
        deadline = monotonic() + self.timeout_seconds
        with self._lock:
            if self._closed:
                return WriteOutcome.CLOSED
            if isinstance(self.repository, NoOpRunRepository):
                return WriteOutcome.STORED
            if self._worker is not None and self._worker.is_alive():
                return WriteOutcome.BUSY
            attempt = _Attempt()
            worker = Thread(
                target=self._save,
                args=(snapshot, attempt),
                name="equity-run-write",
                daemon=True,
            )
            self._worker = worker
            self._saving = True
            try:
                worker.start()
            except Exception:
                self._saving = False
                self._worker = None
                return WriteOutcome.FAILED
        if not attempt.done.wait(max(0.0, deadline - monotonic())):
            return WriteOutcome.TIMED_OUT
        return attempt.outcome

    def _save(self, snapshot: RunSnapshot, attempt: _Attempt) -> None:
        try:
            self.repository.save_run(snapshot)
            attempt.outcome = WriteOutcome.STORED
        except Exception:
            attempt.outcome = WriteOutcome.FAILED
        finally:
            with self._lock:
                self._saving = False
                close_repository = self._closed and not self._close_started
                if close_repository:
                    self._close_started = True
            try:
                if close_repository:
                    self._close_repository()
            finally:
                attempt.done.set()

    def _close_repository(self) -> None:
        try:
            self.repository.close()
        except Exception:
            pass  # Do not expose exception content during application teardown.

    def close(self) -> None:
        """Stop admissions and wait at most one write budget for cleanup.

        Do not dispose a repository concurrently with its unfinished run write.
        If it remains stalled, its daemon owns one bounded slot until process exit;
        if it eventually returns, _save disposes the repository before exiting.
        """
        with self._lock:
            self._closed = True
            if not self._saving and not self._close_started:
                self._close_started = True
                self._worker = Thread(
                    target=self._close_repository,
                    name="equity-run-close",
                    daemon=True,
                )
                self._worker.start()
            worker = self._worker
        if worker is not None:
            worker.join(self.timeout_seconds)
