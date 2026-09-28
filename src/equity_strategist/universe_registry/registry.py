from equity_strategist.domain.errors import AmbiguousUniverseError, UnknownUniverseError
from equity_strategist.domain.universe import Universe


class UniverseRegistry:
    """Registry of known investment universes."""

    def __init__(
        self,
        universes: list[Universe],
    ) -> None:
        self._universes = tuple(universes)
        self._canonical: dict[str, Universe] = {}
        for universe in self._universes:
            name = universe.name.strip().casefold()
            if name in self._canonical:
                raise ValueError("duplicate normalized canonical universe name")
            self._canonical[name] = universe

    def resolve(
        self,
        query: str,
    ) -> Universe:
        clean_query = query.strip().casefold()

        if not clean_query:
            raise ValueError("universe query cannot be empty")

        if clean_query in self._canonical:
            return self._canonical[clean_query]

        matches = [
            universe
            for universe in self._universes
            if self._matches(
                universe,
                clean_query,
            )
        ]

        if not matches:
            raise UnknownUniverseError(f"unknown universe: {query}")

        if len(matches) > 1:
            raise AmbiguousUniverseError(query, tuple(matches))

        return matches[0]

    @staticmethod
    def _matches(
        universe: Universe,
        query: str,
    ) -> bool:
        terms = {
            universe.name.strip().casefold(),
            *(alias.strip().casefold() for alias in universe.aliases),
        }

        return query in terms

    @property
    def universes(self) -> tuple[Universe, ...]:
        return self._universes
