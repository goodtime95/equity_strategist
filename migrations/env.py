"""No URL in Alembic config or logs. Never invoked by application startup."""

import os

from alembic import context

from equity_strategist.persistence.postgres import create_postgres_engine
from equity_strategist.persistence.schema import metadata


def run_migrations() -> None:
    if context.is_offline_mode():
        context.configure(
            dialect_name="postgresql", target_metadata=metadata, literal_binds=True
        )
        with context.begin_transaction():
            context.run_migrations()
        return
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required for migrations")
    engine = create_postgres_engine(url)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


run_migrations()
