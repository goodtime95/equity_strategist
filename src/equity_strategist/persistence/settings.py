import os
from dataclasses import dataclass, field
from math import isfinite


@dataclass(frozen=True)
class PersistenceSettings:
    enabled: bool = False
    persist_content: bool = False
    retention_days: int = 30
    timeout_seconds: float = 2.0
    database_url: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("persistence timeout must be finite and positive")
        if self.retention_days < 1:
            raise ValueError("retention_days must be positive")

    @classmethod
    def from_env(cls) -> "PersistenceSettings":
        return cls(
            enabled=os.getenv("EQUITY_STRATEGIST_PERSISTENCE_ENABLED", "").lower()
            == "true",
            persist_content=os.getenv("EQUITY_STRATEGIST_PERSIST_CONTENT", "").lower()
            == "true",
            retention_days=int(os.getenv("EQUITY_STRATEGIST_RETENTION_DAYS", "30")),
            database_url=os.getenv("DATABASE_URL"),
            timeout_seconds=float(
                os.getenv("EQUITY_STRATEGIST_PERSISTENCE_TIMEOUT_SECONDS", "2")
            ),
        )
