from equity_strategist.domain.universe import (
    Universe,
    UniverseType,
)
from equity_strategist.domain.universe_constituent import (
    UniverseConstituent,
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
    ) -> tuple[UniverseConstituent, ...]:
        if provider_identifier == "CAC40":
            return (
                UniverseConstituent(
                    name="LVMH",
                    isin="FR0000121014",
                    exchange="Paris",
                    provider_symbol="MC",
                ),
                UniverseConstituent(
                    name="Hermès",
                    isin="FR0000052292",
                    exchange="Paris",
                    provider_symbol="RMS",
                ),
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
                provider="fake",
                provider_identifier="CAC40",
            ),
        ]
    )

    return UniverseConstituentService(
        universe_registry=registry,
        universe_providers={
            "fake": FakeUniverseProvider(),
        },
    )


def test_static_universe_returns_registered_assets() -> None:
    service = build_service()

    constituents = service.get_constituents("Luxury Europe")

    assert tuple(item.name for item in constituents) == (
        "LVMH",
        "Hermès",
    )


def test_dynamic_universe_uses_provider() -> None:
    service = build_service()

    constituents = service.get_constituents("CAC 40")

    assert len(constituents) == 2

    assert constituents[0].name == "LVMH"
    assert constituents[0].isin == "FR0000121014"

    assert constituents[1].name == "Hermès"
    assert constituents[1].isin == "FR0000052292"


def test_dynamic_universe_rejects_unknown_provider() -> None:
    registry = UniverseRegistry(
        [
            Universe(
                name="CAC 40",
                universe_type=UniverseType.DYNAMIC,
                provider="unknown",
                provider_identifier="CAC40",
            ),
        ]
    )

    service = UniverseConstituentService(
        universe_registry=registry,
        universe_providers={},
    )

    try:
        service.get_constituents("CAC 40")
    except ValueError as exc:
        assert "unknown universe provider" in str(exc)
    else:
        raise AssertionError("expected ValueError for unknown provider")


def test_dynamic_universe_rejects_empty_constituents() -> None:
    registry = UniverseRegistry(
        [
            Universe(
                name="CAC 40",
                universe_type=UniverseType.DYNAMIC,
                provider="fake",
                provider_identifier="UNKNOWN",
            ),
        ]
    )

    service = UniverseConstituentService(
        universe_registry=registry,
        universe_providers={
            "fake": FakeUniverseProvider(),
        },
    )

    try:
        service.get_constituents("CAC 40")
    except ValueError as exc:
        assert "no constituents found" in str(exc)
    else:
        raise AssertionError("expected ValueError for empty constituents")
