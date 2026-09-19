"""Optional observations, scoped to one invocation and never checkpointed."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from time import perf_counter
from typing import Any


@dataclass(frozen=True)
class Observation:
    stage: str
    duration_ms: float
    failed: bool = False


Observer = Callable[[Observation], None]
_progress: ContextVar[Callable[[str, Any], None] | None] = ContextVar(
    "run_progress", default=None
)


def report_progress(name: str, value: Any) -> None:
    try:
        callback = _progress.get()
        if callback is not None:
            callback(name, value)
    except Exception:
        pass


_observer: ContextVar[Observer | None] = ContextVar("run_observer", default=None)


@contextmanager
def observing(
    observer: Observer | None,
    progress: Callable[[str, Any], None] | None = None,
) -> Iterator[None]:
    token = _observer.set(observer)
    progress_token = _progress.set(progress)
    try:
        yield
    finally:
        _observer.reset(token)
        _progress.reset(progress_token)


@contextmanager
def stage_timing(stage: str) -> Iterator[None]:
    try:
        start = perf_counter()
    except Exception:
        start = None
    failed = False
    try:
        yield
    except Exception:
        failed = True
        raise
    finally:
        try:
            observer = _observer.get()
            if observer is not None and start is not None:
                observer(Observation(stage, (perf_counter() - start) * 1000, failed))
        except Exception:
            pass  # Observability must never affect the analytical path.
