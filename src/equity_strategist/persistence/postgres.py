from dataclasses import asdict
from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError

from equity_strategist.application.run_snapshot import RunSnapshot
from equity_strategist.application.thread_identity import persistent_thread_id
from equity_strategist.persistence.repository import Feedback, UnknownRun
from equity_strategist.persistence.schema import analysis_run, feedback


def create_postgres_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}:
        raise ValueError("PostgreSQL is required")
    return sa.create_engine(
        url.set(drivername="postgresql+psycopg"),
        pool_size=2,
        max_overflow=0,
        pool_timeout=2,
        hide_parameters=True,
        connect_args={
            "connect_timeout": 2,
            "options": "-c statement_timeout=2000 -c lock_timeout=1000",
        },
    )


class PostgresRunRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def save_run(self, snapshot: RunSnapshot) -> None:
        with self.engine.begin() as connection:
            connection.execute(analysis_run.insert().values(**asdict(snapshot)))

    def save_feedback(self, item: Feedback) -> None:
        try:
            with self.engine.begin() as connection:
                connection.execute(feedback.insert().values(**asdict(item)))
        except IntegrityError as error:
            if getattr(error.orig, "sqlstate", None) == "23503":
                raise UnknownRun("Unknown request") from None
            raise

    def _delete(self, predicate: sa.ColumnElement) -> int:
        with self.engine.begin() as connection:
            return connection.execute(analysis_run.delete().where(predicate)).rowcount

    def delete_request(self, request_id: UUID) -> int:
        return self._delete(analysis_run.c.request_id == request_id)

    def delete_thread(self, thread_id: str) -> int:
        return self._delete(analysis_run.c.thread_id == persistent_thread_id(thread_id))

    def cleanup(self, before: datetime) -> int:
        return self._delete(analysis_run.c.created_at < before)

    def close(self) -> None:
        self.engine.dispose()
