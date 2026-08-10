from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Universe:
    """Named investment universe composed of registered assets."""

    name: str
    asset_queries: tuple[str, ...]
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("universe name cannot be empty")

        if not self.asset_queries:
            raise ValueError("universe must contain at least one asset")
