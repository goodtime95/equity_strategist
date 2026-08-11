from dataclasses import dataclass
from enum import StrEnum


class UniverseType(StrEnum):
    STATIC = "static"
    DYNAMIC = "dynamic"


@dataclass(frozen=True, slots=True)
class Universe:
    """Definition of a named investment universe."""

    name: str
    universe_type: UniverseType

    asset_queries: tuple[str, ...] = ()

    provider: str | None = None
    provider_identifier: str | None = None

    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("universe name cannot be empty")

        if self.universe_type == UniverseType.STATIC and not self.asset_queries:
            raise ValueError("static universe requires assets")

        if self.universe_type == UniverseType.DYNAMIC:
            if self.provider is None:
                raise ValueError("dynamic universe requires provider")

            if self.provider_identifier is None:
                raise ValueError("dynamic universe requires provider identifier")
