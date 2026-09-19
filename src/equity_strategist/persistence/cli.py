"""Explicit operator commands; never run cleanup in the analytical path."""

import argparse
from datetime import UTC, datetime, timedelta
from uuid import UUID

from equity_strategist.persistence.postgres import (
    PostgresRunRepository,
    create_postgres_engine,
)
from equity_strategist.persistence.settings import PersistenceSettings


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete persisted pilot runs/feedback")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("cleanup", help="Delete runs older than configured retention")
    commands.add_parser("delete-request").add_argument("request_id", type=UUID)
    commands.add_parser("delete-thread").add_argument("thread_id")
    args = parser.parse_args()
    repository = None
    try:
        settings = PersistenceSettings.from_env()
        if not settings.database_url:
            parser.exit(2, "DATABASE_URL is required for operator commands\n")
        repository = PostgresRunRepository(
            create_postgres_engine(settings.database_url)
        )
        if args.command == "cleanup":
            count = repository.cleanup(
                datetime.now(UTC) - timedelta(days=settings.retention_days)
            )
        elif args.command == "delete-request":
            count = repository.delete_request(args.request_id)
        else:
            count = repository.delete_thread(args.thread_id)
        print(f"Deleted {count} runs and their associated feedback")
    except Exception:
        parser.exit(
            1, "Persistence operation failed; check configuration/connectivity\n"
        )
    finally:
        if repository is not None:
            repository.close()


if __name__ == "__main__":
    main()
