"""Regressions for private thread identity and bounded run recording."""

from dataclasses import asdict
from datetime import date
from threading import Event
from threading import enumerate as live_threads
from time import monotonic
from types import SimpleNamespace
from uuid import uuid4

import pytest
import sqlalchemy as sa
from curl_cffi.requests.exceptions import RequestException
from fastapi.testclient import TestClient
from yfinance.exceptions import YFPricesMissingError, YFRateLimitError

from equity_strategist.api.server import create_app
from equity_strategist.application.run_coordinator import AnalysisRunCoordinator
from equity_strategist.application.run_snapshot import error_category
from equity_strategist.application.thread_identity import persistent_thread_id
from equity_strategist.data_providers.yahoo import YahooFinanceProvider
from equity_strategist.domain.asset import Asset
from equity_strategist.domain.errors import InsufficientDataError, ProviderFailure
from equity_strategist.persistence.postgres import PostgresRunRepository
from equity_strategist.persistence.settings import PersistenceSettings
from tests.test_api import AUTH, FakeGraph
from tests.test_run_telemetry import RecordingRepository, invoke

SENSITIVE_IDS = (
    "client@example.test",
    "a private note about a client",
    "192.0.2.1",
    "Bearer alpha",
    "Bearer beta",
)


@pytest.mark.parametrize("full", [False, True])
def test_persistent_thread_ids_do_not_contain_external_content(full):
    repository = RecordingRepository()
    graph = FakeGraph()
    with TestClient(
        create_app(
            lambda: graph,
            api_key="test-secret",
            repository=repository,
            persistence_settings=PersistenceSettings(persist_content=full),
        )
    ) as client:
        for thread_id in SENSITIVE_IDS:
            response = client.post(
                "/v1/chat",
                headers=AUTH,
                json={
                    "question": "price?",
                    "thread_id": thread_id,
                },
            )
            assert response.status_code == 200
            assert response.json()["thread_id"] == thread_id
            assert graph.calls[-1][1] == thread_id
            snapshot = repository.runs[-1]
            assert snapshot.thread_id == persistent_thread_id(thread_id)
            assert thread_id not in str(asdict(snapshot))
    assert len({item.thread_id for item in repository.runs}) == len(SENSITIVE_IDS)
    assert persistent_thread_id("Bearer alpha") != persistent_thread_id("Bearer beta")
    assert persistent_thread_id("x") != persistent_thread_id(" x")
    assert persistent_thread_id("x") != persistent_thread_id("X")


def test_delete_by_external_thread_id_uses_same_identity_and_only_that_thread():
    # Exercise the actual Core DELETE predicate against an isolated SQL engine.
    # This is not a replacement for PostgreSQL migration/FK acceptance tests.
    engine = sa.create_engine("sqlite://")
    recorder = RecordingRepository()
    coordinator = AnalysisRunCoordinator(recorder)
    for external_id in SENSITIVE_IDS:
        coordinator.run(
            "question",
            external_id,
            lambda: FakeGraph().invoke("question", "irrelevant"),
            lambda result, request_id: result["answer"],
        )
    coordinator.close()
    rows = [(str(run.request_id), run.thread_id) for run in recorder.runs]
    rows.append((str(uuid4()), rows[-1][1]))  # Two runs in the final thread.
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE analysis_run (request_id TEXT, thread_id TEXT)"
            )
            connection.exec_driver_sql("INSERT INTO analysis_run VALUES (?, ?)", rows)
        repository = PostgresRunRepository(engine)
        assert repository.delete_thread(SENSITIVE_IDS[-1]) == 2
        assert repository.delete_thread(SENSITIVE_IDS[-1]) == 0
        with engine.connect() as connection:
            remaining = (
                connection.exec_driver_sql("SELECT thread_id FROM analysis_run")
                .scalars()
                .all()
            )
        assert set(remaining) == {persistent_thread_id(t) for t in SENSITIVE_IDS[:-1]}
    finally:
        engine.dispose()


class StallingRepository(RecordingRepository):
    def __init__(self):
        super().__init__()
        self.entered = Event()
        self.release = Event()
        self.finished = Event()
        self.closed = Event()
        self.calls = 0
        self.close_calls = 0

    def save_run(self, snapshot):
        self.calls += 1
        self.entered.set()
        try:
            assert self.release.wait(5), "test must release the stalled operation"
            super().save_run(snapshot)
        finally:
            self.finished.set()

    def close(self):
        assert self.finished.is_set(), "must not close during a write"
        self.close_calls += 1
        self.closed.set()


def test_stalled_write_returns_unchanged_response_and_drops_further_admissions(caplog):
    repository = StallingRepository()
    coordinator = AnalysisRunCoordinator(repository, persistence_timeout_seconds=0.03)
    expected = object()
    graph_result = FakeGraph().invoke("q", "external")
    try:
        started = monotonic()
        run = coordinator.run(
            "private question",
            "private thread",
            lambda: graph_result,
            lambda result, request_id: expected,
        )
        assert monotonic() - started < 0.5
        assert repository.entered.is_set() and not repository.finished.is_set()
        assert not run.failed and run.response is expected
        assert "run_persistence_timed_out" in caplog.text
        workers = [t for t in live_threads() if t.name == "equity-run-write"]
        assert len(workers) == 1 and workers[0].daemon

        started = monotonic()
        for _ in range(25):
            following = coordinator.run(
                "private question",
                "private thread",
                lambda: graph_result,
                lambda result, request_id: expected,
            )
            assert following.response is expected and not following.failed
        assert monotonic() - started < 0.5
        assert repository.calls == 1
        assert [t for t in live_threads() if t.name == "equity-run-write"] == workers
        assert "run_persistence_busy" in caplog.text
        assert "private" not in caplog.text
        assert all(record.exc_info is None for record in caplog.records)
    finally:
        repository.release.set()
        coordinator.close()
    assert repository.closed.wait(1)
    assert repository.close_calls == 1


def test_shutdown_is_bounded_and_eventually_disposes_timed_out_writer():
    repository = StallingRepository()
    coordinator = AnalysisRunCoordinator(repository, persistence_timeout_seconds=0.03)
    try:
        assert not invoke(coordinator).failed
        started = monotonic()
        coordinator.close()
        assert monotonic() - started < 0.5
        assert not repository.closed.is_set()
        assert not invoke(coordinator).failed  # Analysis survives closed persistence.
        assert repository.calls == 1
    finally:
        repository.release.set()
    assert repository.closed.wait(1)
    coordinator.close()
    assert repository.close_calls == 1


def test_stalled_recording_of_analysis_error_is_also_bounded():
    repository = StallingRepository()
    coordinator = AnalysisRunCoordinator(repository, persistence_timeout_seconds=0.03)

    def fail():
        raise InsufficientDataError("private")

    try:
        started = monotonic()
        run = coordinator.run("q", "t", fail, lambda result, request_id: None)
        assert monotonic() - started < 0.5
        assert run.failed and run.error_category == "insufficient_data"
        assert repository.entered.is_set() and not repository.finished.is_set()
    finally:
        repository.release.set()
        coordinator.close()


def test_writer_recovers_after_stalled_operation_finishes():
    repository = StallingRepository()
    coordinator = AnalysisRunCoordinator(repository, persistence_timeout_seconds=0.03)
    try:
        assert not invoke(coordinator).failed
        repository.release.set()
        worker = next(t for t in live_threads() if t.name == "equity-run-write")
        worker.join(1)
        assert not worker.is_alive()
        assert not invoke(coordinator).failed
        assert repository.calls == 2
    finally:
        repository.release.set()
        coordinator.close()


def test_api_shutdown_does_not_wait_for_stalled_database():
    repository = StallingRepository()
    started = monotonic()
    try:
        with TestClient(
            create_app(
                FakeGraph,
                api_key="test-secret",
                repository=repository,
                persistence_settings=PersistenceSettings(timeout_seconds=0.03),
            )
        ) as client:
            response = client.post("/v1/chat", headers=AUTH, json={"question": "test"})
            assert response.status_code == 200
            assert response.json()["answer"] == "fake answer"
        assert monotonic() - started < 0.75
        assert not repository.finished.is_set()
    finally:
        repository.release.set()
    assert repository.closed.wait(1)


@pytest.mark.parametrize(
    ("failure", "expected_type", "category"),
    [
        (
            YFPricesMissingError("TEST", "private"),
            InsufficientDataError,
            "insufficient_data",
        ),
        (YFRateLimitError(), ProviderFailure, "provider_failure"),
        (RequestException("private"), ProviderFailure, "provider_failure"),
        (ValueError("prices missing"), ValueError, "internal_error"),
    ],
)
def test_yahoo_price_failures_are_classified_by_type(
    monkeypatch,
    failure,
    expected_type,
    category,
):
    def fail(**kwargs):
        raise failure

    monkeypatch.setattr(
        "equity_strategist.data_providers.yahoo.yf.Ticker",
        lambda symbol: SimpleNamespace(history=fail),
    )
    with pytest.raises(expected_type) as caught:
        YahooFinanceProvider().get_daily_prices(
            Asset("TEST"),
            date(2024, 1, 1),
            date(2024, 2, 1),
        )
    assert error_category(caught.value) == category


@pytest.mark.parametrize("budget", [0, -1, float("inf"), float("nan")])
def test_invalid_persistence_budget_is_rejected(budget):
    with pytest.raises(ValueError):
        PersistenceSettings(timeout_seconds=budget)
    with pytest.raises(ValueError):
        AnalysisRunCoordinator(persistence_timeout_seconds=budget)


def test_persistence_budget_is_configurable(monkeypatch):
    monkeypatch.setenv("EQUITY_STRATEGIST_PERSISTENCE_TIMEOUT_SECONDS", "0.05")
    assert PersistenceSettings.from_env().timeout_seconds == 0.05


def test_concurrent_stalled_writes_share_one_admission_slot():
    from concurrent.futures import ThreadPoolExecutor

    repository = StallingRepository()
    coordinator = AnalysisRunCoordinator(repository, persistence_timeout_seconds=0.03)
    try:
        with ThreadPoolExecutor(max_workers=8) as callers:
            responses = list(callers.map(lambda _: invoke(coordinator), range(16)))
        assert all(not response.failed for response in responses)
        assert repository.calls == 1
        assert not repository.finished.is_set()
    finally:
        repository.release.set()
        coordinator.close()


def test_stalled_driver_does_not_prevent_process_exit():
    import subprocess
    import sys
    import textwrap

    child = subprocess.run(
        [
            sys.executable,
            "-c",
            textwrap.dedent("""
            from threading import Event
            from equity_strategist.application.run_coordinator import (
                AnalysisRunCoordinator,
            )
            from tests.test_run_telemetry import invoke
            class Repository:
                def save_run(self, snapshot):
                    Event().wait()
                def close(self):
                    raise AssertionError("must not close during stalled save")
            coordinator = AnalysisRunCoordinator(
                Repository(), persistence_timeout_seconds=0.03,
            )
            assert not invoke(coordinator).failed
            coordinator.close()
            print("completed")
        """),
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )
    assert child.stdout.strip() == "completed"


def test_repository_close_itself_is_bounded_and_runs_once():
    class StalledClose(RecordingRepository):
        def __init__(self):
            super().__init__()
            self.entered = Event()
            self.release = Event()
            self.finished = Event()
            self.calls = 0

        def close(self):
            self.calls += 1
            self.entered.set()
            try:
                assert self.release.wait(5)
            finally:
                self.finished.set()

    repository = StalledClose()
    coordinator = AnalysisRunCoordinator(repository, persistence_timeout_seconds=0.03)
    try:
        started = monotonic()
        coordinator.close()
        coordinator.close()
        assert monotonic() - started < 0.5
        assert repository.entered.is_set() and not repository.finished.is_set()
        assert repository.calls == 1
    finally:
        repository.release.set()
    assert repository.finished.wait(1)
