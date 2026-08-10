from equity_strategist.domain.universe import Universe


class UniverseRegistry:
    """Registry of known investment universes."""

    def __init__(
        self,
        universes: list[Universe],
    ) -> None:
        self._universes = tuple(universes)

    def resolve(
        self,
        query: str,
    ) -> Universe:
        clean_query = query.strip().casefold()

        if not clean_query:
            raise ValueError("universe query cannot be empty")

        matches = [
            universe
            for universe in self._universes
            if self._matches(
                universe,
                clean_query,
            )
        ]

        if not matches:
            raise ValueError(f"unknown universe: {query}")

        if len(matches) > 1:
            raise ValueError(f"ambiguous universe: {query}")

        return matches[0]

    @staticmethod
    def _matches(
        universe: Universe,
        query: str,
    ) -> bool:
        terms = {
            universe.name.casefold(),
            *(alias.casefold() for alias in universe.aliases),
        }

        return query in terms

    @property
    def universes(self) -> tuple[Universe, ...]:
        return self._universes
