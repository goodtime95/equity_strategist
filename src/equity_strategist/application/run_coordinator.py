"""Application lifecycle around the independent analytical engine."""

import json
import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from traceback import walk_tb
from typing import TypeVar
from uuid import UUID, uuid4

from equity_strategist.application.run_snapshot import build_snapshot, error_category
from equity_strategist.application.run_writer import BoundedRunWriter, WriteOutcome
from equity_strategist.application.telemetry import Observation, observing, stage_timing
from equity_strategist.persistence.repository import NoOpRunRepository, RunRepository
from equity_strategist.strategists.graph_state import EquityGraphResult

LOGGER = logging.getLogger(__name__)
T = TypeVar("T")


@dataclass(frozen=True)
class RunResponse[T]:
    request_id: UUID
    response: T | None
    failed: bool
    error_category: str | None = None
    failure_stage: str | None = None


class AnalysisRunCoordinator:
    def __init__(
        self,
        repository: RunRepository | None = None,
        *,
        persist_content: bool = False,
        model_metadata: dict[str, str] | None = None,
        git_version: str | None = None,
        secret_values: tuple[str, ...] = (),
        persistence_timeout_seconds: float = 2.0,
    ) -> None:
        self.repository = repository or NoOpRunRepository()
        self._writer = BoundedRunWriter(self.repository, persistence_timeout_seconds)
        self.persist_content = persist_content
        self.model_metadata = model_metadata or {}
        self.git_version = git_version
        self.secret_values = secret_values
        try:
            self.app_version = version("equity-strategist")
        except Exception:
            self.app_version = None

    def run(
        self,
        question: str,
        thread_id: str,
        invoke: Callable[[], EquityGraphResult],
        serialize: Callable[[EquityGraphResult, str], T],
    ) -> RunResponse[T]:
        request_id = uuid4()
        created_at = datetime.now(UTC)
        started = perf_counter()
        observations: list[Observation] = []
        progress: EquityGraphResult = {}
        execution_step: str | None = None

        def observe_progress(name: str, value: object) -> None:
            nonlocal execution_step
            if name == "execution_step":
                execution_step = value
            else:
                progress[name] = value

        result = None
        response = None
        error = None
        failure_stage = "graph_invocation"
        with observing(observations.append, observe_progress):
            try:
                result = invoke()
                failure_stage = "response_serialization"
                with stage_timing("serialization"):
                    response = serialize(result, str(request_id))
            except Exception as caught:
                error = caught
        completed_at = datetime.now(UTC)
        duration_ms = (perf_counter() - started) * 1000
        failed_stages = [item.stage for item in observations if item.failed]
        if failed_stages:
            failure_stage = failed_stages[-1]
            if failure_stage == "serialization":
                failure_stage = "response_serialization"
        if error is not None:
            self._log_failure(request_id, failure_stage, execution_step, error)
        # Snapshot construction is inside the same failure firewall as storage.
        try:
            snapshot = build_snapshot(
                request_id=request_id,
                thread_id=thread_id,
                created_at=created_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                question=question,
                result=result or progress,
                error=error,
                failure_stage=failure_stage,
                telemetry={"stages": [asdict(item) for item in observations]},
                persist_content=self.persist_content,
                model_metadata=self.model_metadata,
                app_version=self.app_version,
                git_version=self.git_version,
                secret_values=self.secret_values,
            )
            outcome = self._writer.write(snapshot)
            if outcome != WriteOutcome.STORED:
                self._log_persistence(outcome, request_id)
        except Exception:
            self._log_persistence(WriteOutcome.FAILED, request_id)
        return RunResponse(
            request_id,
            response,
            error is not None,
            error_category(error),
            failure_stage if error else None,
        )

    @staticmethod
    def _log_failure(
        request_id: UUID, stage: str, step: str | None, error: Exception
    ) -> None:
        """Log stack locations, never exception payloads, locals or source lines."""
        try:
            LOGGER.error(
                "%s",
                json.dumps(
                    {
                        "event": "analysis_failed",
                        "request_id": str(request_id),
                        "stage": stage,
                        "step": step if stage == "execution" else None,
                        "exception_type": type(error).__name__,
                        "message": "Analysis failed; exception payload withheld",
                        "traceback": [
                            {
                                "file": Path(frame.f_code.co_filename).name,
                                "function": frame.f_code.co_name,
                                "line": line,
                            }
                            for frame, line in walk_tb(error.__traceback__)
                        ],
                    }
                ),
            )
        except Exception:
            pass  # A broken logging sink must not suppress the public error.

    @staticmethod
    def _log_persistence(outcome: WriteOutcome, request_id: UUID) -> None:
        try:
            LOGGER.warning(
                "run_persistence_%s request_id=%s", outcome.value, request_id
            )
        except Exception:
            pass  # A broken logging sink cannot invalidate an analysis.

    def close(self) -> None:
        self._writer.close()
