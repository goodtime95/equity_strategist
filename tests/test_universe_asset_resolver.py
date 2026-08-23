import pytest

from equity_strategist.asset_registry import (
    build_default_asset_registry,
)
from equity_strategist.domain.asset import Asset
from equity_strategist.domain.universe_constituent import (
    UniverseConstituent,
)
from equity_strategist.tools.assets import AssetResolver
from equity_strategist.tools.exceptions import AssetNotFoundError
from equity_strategist.tools.universe_assets import (
    UniverseAssetResolver,
)


class FakeMarketDataProvider:
    def search_assets(
        self,
        query: str,
    ) -> list[Asset]:
        if query == "Air Liquide":
            return [
                Asset(
                    symbol="AI.PA",
                    name="Air Liquide",
                    exchange="Paris",
                    currency="EUR",
                    isin="FR0000120073",
                )
            ]

        return []

    def select_primary_asset(
        self,
        assets: list[Asset],
    ) -> Asset | None:
        if len(assets) == 1:
            return assets[0]

        return None

def build_resolver() -> UniverseAssetResolver:
    registry = build_default_asset_registry()
    provider = FakeMarketDataProvider()

    asset_resolver = AssetResolver(
        registry=registry,
        fallback_provider=provider,
    )

    return UniverseAssetResolver(
        asset_resolver=asset_resolver,
    )


def test_resolve_registered_constituent_by_isin() -> None:
    resolver = build_resolver()

    constituent = UniverseConstituent(
        name="Provider LVMH Name",
        isin="FR0000121014",
        exchange="Paris",
    )

    asset = resolver.resolve(constituent)

    assert asset.symbol == "MC.PA"
    assert asset.name == "LVMH Moët Hennessy Louis Vuitton"


def test_resolve_registered_constituent_by_name() -> None:
    resolver = build_resolver()

    constituent = UniverseConstituent(
        name="Hermès",
        exchange="Paris",
    )

    asset = resolver.resolve(constituent)

    assert asset.symbol == "RMS.PA"


def test_resolve_unknown_constituent_from_provider() -> None:
    resolver = build_resolver()

    constituent = UniverseConstituent(
        name="Air Liquide",
        isin="FR0000120073",
        exchange="Paris",
    )

    asset = resolver.resolve(constituent)

    assert asset.symbol == "AI.PA"
    assert asset.name == "Air Liquide"
    assert asset.currency == "EUR"


def test_resolve_many_constituents() -> None:
    resolver = build_resolver()

    assets = resolver.resolve_many(
        (
            UniverseConstituent(
                name="LVMH",
                isin="FR0000121014",
                exchange="Paris",
            ),
            UniverseConstituent(
                name="Hermès",
                isin="FR0000052292",
                exchange="Paris",
            ),
            UniverseConstituent(
                name="Air Liquide",
                isin="FR0000120073",
                exchange="Paris",
            ),
        )
    )

    assert tuple(asset.symbol for asset in assets) == (
        "MC.PA",
        "RMS.PA",
        "AI.PA",
    )


def test_unknown_constituent_fails() -> None:
    resolver = build_resolver()

    with pytest.raises(
        AssetNotFoundError,
        match="Unable to resolve universe constituent",
    ):
        resolver.resolve(
            UniverseConstituent(
                name="Unknown Company",
                isin="XX0000000000",
                exchange="Unknown",
            )
        )


def test_universe_resolver_retries_without_exchange_preference() -> None:
    constituent = UniverseConstituent(
        name="ArcelorMittal SA",
        exchange="Paris",
    )

    class FakeAssetResolver:
        def __init__(self) -> None:
            self.calls = []

        def resolve(
            self,
            query: str,
            preferred_currency=None,
            preferred_exchange=None,
        ) -> Asset:
            self.calls.append(
                (
                    query,
                    preferred_exchange,
                )
            )

            if preferred_exchange is not None:
                raise AssetNotFoundError("No matching preferred exchange")

            return Asset(
                symbol="MT.AS",
                name="ArcelorMittal S.A.",
                exchange="Amsterdam",
                currency="EUR",
            )

    asset_resolver = FakeAssetResolver()

    resolver = UniverseAssetResolver(
        asset_resolver=asset_resolver,
    )

    asset = resolver.resolve(constituent)

    assert asset.symbol == "MT.AS"

    assert (
        "ArcelorMittal SA",
        "Paris",
    ) in asset_resolver.calls

    assert (
        "ArcelorMittal SA",
        None,
    ) in asset_resolver.calls
