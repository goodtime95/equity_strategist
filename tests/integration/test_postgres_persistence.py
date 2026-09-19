"""Opt-in real PostgreSQL checks; isolated schema, no production data deletion."""

import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from equity_strategist.application.run_coordinator import AnalysisRunCoordinator
from equity_strategist.application.thread_identity import persistent_thread_id
from equity_strategist.persistence.postgres import (
    PostgresRunRepository,
    create_postgres_engine,
)
from equity_strategist.persistence.repository import Feedback, UnknownRun
from equity_strategist.persistence.schema import analysis_run, feedback
from tests.test_run_telemetry import RecordingRepository, invoke

pytestmark = pytest.mark.postgres


@pytest.fixture
def repository(monkeypatch):
    url = os.getenv("EQUITY_STRATEGIST_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set EQUITY_STRATEGIST_TEST_DATABASE_URL to opt in")
    # Each run owns a unique schema in the explicitly supplied test database.
    engine = create_postgres_engine(url)
    schema = "test_telemetry_" + uuid4().hex
    with engine.begin() as connection:
        connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
    scoped_url = sa.engine.make_url(url).update_query_dict(
        {
            "options": f"-c search_path={schema}",
        }
    )

    # Engine connect_args also sets timeouts; add search_path in connect_args.
    def scoped_engine(database_url):
        scoped = create_postgres_engine(database_url)

        @sa.event.listens_for(scoped, "connect")
        def set_schema(dbapi_connection, connection_record):
            with dbapi_connection.cursor() as cursor:
                cursor.execute(f'SET search_path TO "{schema}"')
            dbapi_connection.commit()

        return scoped

    import equity_strategist.persistence.postgres as module

    monkeypatch.setattr(module, "create_postgres_engine", scoped_engine)
    monkeypatch.setenv("DATABASE_URL", scoped_url.render_as_string(hide_password=False))
    config = Config("alembic.ini")
    repo = None
    try:
        command.upgrade(config, "head")
        command.upgrade(config, "head")  # A second deploy is a no-op.
        repo = PostgresRunRepository(scoped_engine(url))
        yield repo
        repo.close()
        repo = None
        command.downgrade(config, "base")
        command.upgrade(config, "head")
    finally:
        if repo:
            repo.close()
        with engine.begin() as connection:
            connection.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def snapshot():
    recorder = RecordingRepository()
    invoke(AnalysisRunCoordinator(recorder, persist_content=True))
    return recorder.runs[0]


def test_roundtrip_feedback_fk_and_cascade(repository):
    run = snapshot()
    repository.save_run(run)
    repository.save_feedback(
        Feedback(uuid4(), run.request_id, True, "useful", datetime.now(UTC))
    )
    with repository.engine.connect() as connection:
        stored = connection.execute(sa.select(analysis_run)).mappings().one()
        assert stored["evidence_json"] == run.evidence_json
        assert stored["created_at"] == run.created_at
        assert (
            connection.execute(
                sa.select(sa.func.count()).select_from(feedback)
            ).scalar_one()
            == 1
        )
    with pytest.raises(UnknownRun):
        repository.save_feedback(
            Feedback(uuid4(), uuid4(), False, None, datetime.now(UTC))
        )
    assert repository.delete_request(run.request_id) == 1
    with repository.engine.connect() as connection:
        assert (
            connection.execute(
                sa.select(sa.func.count()).select_from(feedback)
            ).scalar_one()
            == 0
        )


def test_retention_and_thread_delete(repository):
    run = snapshot()
    cutoff = datetime.now(UTC) - timedelta(days=30)
    repository.save_run(replace(run, created_at=cutoff - timedelta(seconds=1)))
    at_cutoff = replace(run, request_id=uuid4(), created_at=cutoff)
    fresh = replace(
        run, request_id=uuid4(), thread_id=persistent_thread_id("another-thread")
    )
    repository.save_run(at_cutoff)
    repository.save_run(fresh)
    assert repository.cleanup(cutoff) == 1
    assert repository.delete_thread("pilot-thread") == 1
    assert repository.delete_request(fresh.request_id) == 1


def test_private_thread_identity_and_cascading_delete(repository):
    external_ids = ("Bearer alpha", "Bearer beta", "client@example.test 192.0.2.1")
    run = snapshot()
    for external in external_ids:
        item = replace(
            run, request_id=uuid4(), thread_id=persistent_thread_id(external)
        )
        repository.save_run(item)
        repository.save_feedback(
            Feedback(uuid4(), item.request_id, True, None, datetime.now(UTC))
        )
    assert repository.delete_thread("Bearer alpha") == 1
    with repository.engine.connect() as connection:
        assert set(
            connection.execute(sa.select(analysis_run.c.thread_id)).scalars()
        ) == {persistent_thread_id(external) for external in external_ids[1:]}
        assert (
            connection.execute(
                sa.select(sa.func.count()).select_from(feedback)
            ).scalar_one()
            == 2
        )
    with pytest.raises(sa.exc.IntegrityError):
        repository.save_run(
            replace(run, request_id=uuid4(), thread_id="raw private text")
        )
