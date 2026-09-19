from datetime import UTC, datetime
from io import StringIO
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from equity_strategist.api.server import create_app
from equity_strategist.application.run_coordinator import AnalysisRunCoordinator
from equity_strategist.persistence.postgres import (
    PostgresRunRepository,
    create_postgres_engine,
)
from equity_strategist.persistence.repository import (
    Feedback,
    NoOpRunRepository,
    StorageUnavailable,
    UnknownRun,
)
from equity_strategist.persistence.schema import analysis_run, feedback, metadata
from equity_strategist.persistence.settings import PersistenceSettings
from tests.test_api import AUTH, FakeGraph
from tests.test_run_telemetry import RecordingRepository, invoke


def test_unconfigured_startup_never_needs_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("EQUITY_STRATEGIST_PERSISTENCE_ENABLED", raising=False)
    with TestClient(create_app(FakeGraph, api_key="test-secret")) as client:
        assert (
            client.post("/v1/chat", headers=AUTH, json={"question": "test"}).status_code
            == 200
        )
        assert (
            client.post(
                "/v1/feedback",
                headers=AUTH,
                json={
                    "request_id": str(uuid4()),
                    "useful": True,
                },
            ).status_code
            == 503
        )


@pytest.mark.parametrize("url", [None, "bad-url", "sqlite://"])
def test_invalid_database_configuration_does_not_block_analysis(url):
    settings = PersistenceSettings(enabled=True, database_url=url)
    with TestClient(
        create_app(FakeGraph, api_key="test-secret", persistence_settings=settings)
    ) as client:
        assert (
            client.post("/v1/chat", headers=AUTH, json={"question": "test"}).status_code
            == 200
        )


@pytest.mark.parametrize("full", [True, False])
def test_feedback_auth_contract_and_content_policy(full):
    repository = RecordingRepository()
    client = TestClient(
        create_app(
            FakeGraph,
            api_key="test-secret",
            repository=repository,
            persistence_settings=PersistenceSettings(persist_content=full),
        )
    )
    payload = {"request_id": str(uuid4()), "useful": False, "comment": "useful detail"}
    assert client.post("/v1/feedback", json=payload).status_code == 401
    response = client.post("/v1/feedback", headers=AUTH, json=payload)
    assert response.status_code == 201
    assert response.json()["status"] == "stored"
    assert repository.feedback[0].useful is False
    assert repository.feedback[0].comment == ("useful detail" if full else None)
    for invalid in (
        {**payload, "comment": "x" * 2001},
        {**payload, "useful": "yes"},
        {**payload, "request_id": "invalid"},
        {**payload, "headers": {}},
    ):
        assert (
            client.post("/v1/feedback", headers=AUTH, json=invalid).status_code == 422
        )
    assert (
        client.post("/v1/feedback", headers=AUTH, content=b"x" * 65537).status_code
        == 413
    )


@pytest.mark.parametrize(
    ("exception", "status"),
    [
        (UnknownRun("private"), 404),
        (RuntimeError("private"), 503),
    ],
)
def test_feedback_storage_failure_is_explicit(exception, status):
    class BrokenRepository(RecordingRepository):
        def save_feedback(self, item):
            raise exception

    client = TestClient(
        create_app(FakeGraph, api_key="test-secret", repository=BrokenRepository())
    )
    response = client.post(
        "/v1/feedback", headers=AUTH, json={"request_id": str(uuid4()), "useful": True}
    )
    assert response.status_code == status
    assert "private" not in response.text


def test_noop_does_not_claim_feedback_was_stored():
    with pytest.raises(StorageUnavailable):
        NoOpRunRepository().save_feedback(
            Feedback(uuid4(), uuid4(), True, None, datetime.now(UTC))
        )


def test_schema_and_offline_migration():
    assert set(metadata.tables) == {"analysis_run", "feedback"}
    sql = str(CreateTable(analysis_run).compile(dialect=postgresql.dialect()))
    assert "JSONB" in sql and "TIMESTAMP WITH TIME ZONE" in sql
    assert next(iter(feedback.c.request_id.foreign_keys)).ondelete == "CASCADE"
    output = StringIO()
    config = Config("alembic.ini", output_buffer=output)
    command.upgrade(config, "head", sql=True)
    migration = output.getvalue()
    for table in ("analysis_run", "feedback"):
        assert f"CREATE TABLE {table}" in migration
    assert "ON DELETE CASCADE" in migration
    assert "ix_analysis_run_created_at" in migration


def test_engine_creation_does_not_connect_and_forces_psycopg(monkeypatch):
    calls = []
    import equity_strategist.persistence.postgres as module

    monkeypatch.setattr(
        module.sa, "create_engine", lambda url, **kw: calls.append((url, kw))
    )
    create_postgres_engine("postgresql://user:password@localhost/test")
    assert calls[0][0].drivername == "postgresql+psycopg"
    assert calls[0][1]["hide_parameters"] is True
    assert calls[0][1]["connect_args"]["connect_timeout"] == 2


def test_repository_transactions_only_surround_writes():
    from contextlib import contextmanager

    events = []

    class Engine:
        @contextmanager
        def begin(self):
            events.append("begin")
            yield self
            events.append("commit")

        def execute(self, statement):
            events.append("write")

    repository = PostgresRunRepository(Engine())
    coordinator = AnalysisRunCoordinator(repository)

    class Graph(FakeGraph):
        def invoke(self, question, thread_id):
            assert not events
            events.append("graph")
            return super().invoke(question, thread_id)

    assert not invoke(coordinator, Graph()).failed
    assert events == ["graph", "begin", "write", "commit"]


def test_settings_defaults_and_secret_repr(monkeypatch):
    for name in ("PERSISTENCE_ENABLED", "PERSIST_CONTENT", "RETENTION_DAYS"):
        monkeypatch.delenv("EQUITY_STRATEGIST_" + name, raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://secret")
    settings = PersistenceSettings.from_env()
    assert not settings.enabled and not settings.persist_content
    assert settings.retention_days == 30
    assert "secret" not in repr(settings)
    with pytest.raises(ValueError):
        PersistenceSettings(retention_days=0)


@pytest.mark.parametrize(
    ("args", "method"),
    [
        (["cleanup"], "cleanup"),
        (["delete-request", "00000000-0000-0000-0000-000000000001"], "delete_request"),
        (["delete-thread", "pilot-thread"], "delete_thread"),
    ],
)
def test_operator_commands(monkeypatch, capsys, args, method):
    import equity_strategist.persistence.cli as cli

    calls = []

    class Repository:
        def cleanup(self, cutoff):
            assert 29 < (datetime.now(UTC) - cutoff).total_seconds() / 86400 < 31
            calls.append("cleanup")
            return 1

        def delete_request(self, request_id):
            assert str(request_id) == args[1]
            calls.append("delete_request")
            return 1

        def delete_thread(self, thread_id):
            assert thread_id == "pilot-thread"
            calls.append("delete_thread")
            return 1

        def close(self):
            calls.append("close")

    monkeypatch.setenv("DATABASE_URL", "postgresql://private")
    monkeypatch.setenv("EQUITY_STRATEGIST_RETENTION_DAYS", "30")
    monkeypatch.setattr("sys.argv", ["retention", *args])
    monkeypatch.setattr(cli, "create_postgres_engine", lambda url: None)
    monkeypatch.setattr(cli, "PostgresRunRepository", lambda engine: Repository())
    cli.main()
    assert calls == [method, "close"]
    assert "Deleted 1 runs" in capsys.readouterr().out


def test_injected_auth_key_never_enters_full_snapshot():
    repository = RecordingRepository()
    client = TestClient(
        create_app(
            FakeGraph,
            api_key="test-secret",
            repository=repository,
            persistence_settings=PersistenceSettings(persist_content=True),
        )
    )
    response = client.post("/v1/chat", headers=AUTH, json={"question": "test-secret"})
    assert response.status_code == 200
    assert "test-secret" not in repository.runs[0].question
