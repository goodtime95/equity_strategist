from equity_strategist.domain.universe import (
    Universe,
    UniverseType,
)
from equity_strategist.services.universe_constituents import (
    UniverseConstituentService,
)
from equity_strategist.universe_registry.registry import (
    UniverseRegistry,
)


class FakeUniverseProvider:
    def get_constituents(
        self,
        provider_identifier: str,
    ) -> tuple[str, ...]:
        if provider_identifier == "CAC40":
            return (
                "LVMH",
                "Hermès",
            )

        return ()


def build_service() -> UniverseConstituentService:
    registry = UniverseRegistry(
        [
            Universe(
                name="Luxury Europe",
                universe_type=UniverseType.STATIC,
                asset_queries=(
                    "LVMH",
                    "Hermès",
                ),
            ),
            Universe(
                name="CAC 40",
                universe_type=UniverseType.DYNAMIC,
                provider_identifier="CAC40",
            ),
        ]
    )

    return UniverseConstituentService(
        universe_registry=registry,
        universe_provider=FakeUniverseProvider(),
    )


def test_static_universe_returns_registered_assets() -> None:
    service = build_service()

    constituents = service.get_constituents("Luxury Europe")

    assert constituents == (
        "LVMH",
        "Hermès",
    )


def test_dynamic_universe_uses_provider() -> None:
    service = build_service()

    constituents = service.get_constituents("CAC 40")

    assert constituents == (
        "LVMH",
        "Hermès",
    )
