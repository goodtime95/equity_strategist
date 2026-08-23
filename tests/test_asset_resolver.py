import pytest

from equity_strategist.asset_registry.registry import AssetRegistry
from equity_strategist.domain.asset import Asset
from equity_strategist.tools.assets import AssetResolver
from equity_strategist.tools.exceptions import (
    AmbiguousAssetError,
    AssetNotFoundError,
)


class FakeMarketDataProvider:
    def __init__(
        self,
        assets: list[Asset],
        primary_asset: Asset | None = None,
    ) -> None:
        self.assets = assets
        self.primary_asset = primary_asset

    def search_assets(
        self,
        query: str,
    ) -> list[Asset]:
        return self.assets

    def select_primary_asset(
        self,
        assets: list[Asset],
    ) -> Asset | None:
        return self.primary_asset


def build_registry() -> AssetRegistry:
    return AssetRegistry(
        [
            Asset(
                symbol="MC.PA",
                name="LVMH",
                exchange="Paris",
                currency="EUR",
                isin="FR0000121014",
                aliases=("Louis Vuitton",),
            ),
            Asset(
                symbol="LVMUY",
                name="LVMH ADR",
                exchange="OTC Markets",
                currency="USD",
                aliases=("LVMH",),
            ),
        ]
    )


def test_resolve_exact_symbol() -> None:
    resolver = AssetResolver(build_registry())

    result = resolver.resolve("MC.PA")

    assert result.symbol == "MC.PA"


def test_resolve_exact_isin() -> None:
    resolver = AssetResolver(build_registry())

    result = resolver.resolve("FR0000121014")

    assert result.symbol == "MC.PA"


def test_resolve_alias_using_preferred_exchange() -> None:
    resolver = AssetResolver(build_registry())

    result = resolver.resolve(
        "LVMH",
        preferred_exchange="Paris",
    )

    assert result.symbol == "MC.PA"


def test_resolve_alias_using_preferred_currency() -> None:
    resolver = AssetResolver(build_registry())

    result = resolver.resolve(
        "LVMH",
        preferred_currency="EUR",
    )

    assert result.symbol == "MC.PA"


def test_resolve_raises_when_no_asset_is_found() -> None:
    resolver = AssetResolver(build_registry())

    with pytest.raises(AssetNotFoundError):
        resolver.resolve("Unknown company")


def test_resolve_raises_when_query_is_ambiguous() -> None:
    resolver = AssetResolver(build_registry())

    with pytest.raises(AmbiguousAssetError):
        resolver.resolve("LVMH")


def test_resolver_falls_back_to_provider() -> None:
    registry = AssetRegistry(
        assets=[],
    )

    provider = FakeMarketDataProvider(
        assets=[
            Asset(
                symbol="SU.PA",
                name="Schneider Electric",
                exchange="Paris",
                currency="EUR",
            )
        ]
    )

    resolver = AssetResolver(
        registry=registry,
        fallback_provider=provider,
    )

    asset = resolver.resolve("Schneider Electric")

    assert asset.symbol == "SU.PA"
    assert asset.name == "Schneider Electric"


def test_resolver_prefers_registry_before_fallback() -> None:
    registered_asset = Asset(
        symbol="MC.PA",
        name="LVMH",
        currency="EUR",
    )

    registry = AssetRegistry(
        assets=[registered_asset],
    )

    provider = FakeMarketDataProvider(
        assets=[
            Asset(
                symbol="OTHER",
                name="Other Asset",
            )
        ]
    )

    resolver = AssetResolver(
        registry=registry,
        fallback_provider=provider,
    )

    asset = resolver.resolve("LVMH")

    assert asset == registered_asset


def test_resolver_raises_when_fallback_is_ambiguous() -> None:
    registry = AssetRegistry(
        assets=[],
    )

    provider = FakeMarketDataProvider(
        assets=[
            Asset(
                symbol="ABC.PA",
                name="ABC",
            ),
            Asset(
                symbol="ABC.L",
                name="ABC",
            ),
        ]
    )

    resolver = AssetResolver(
        registry=registry,
        fallback_provider=provider,
    )

    with pytest.raises(
        AmbiguousAssetError,
        match="Several external assets",
    ):
        resolver.resolve("ABC")


def test_resolver_raises_when_fallback_finds_nothing() -> None:
    registry = AssetRegistry(
        assets=[],
    )

    provider = FakeMarketDataProvider(
        assets=[],
    )

    resolver = AssetResolver(
        registry=registry,
        fallback_provider=provider,
    )

    with pytest.raises(
        AssetNotFoundError,
        match="No asset found",
    ):
        resolver.resolve("Unknown Company")


def test_resolver_keeps_multiple_external_listings_ambiguous() -> None:
    registry = AssetRegistry(
        assets=[],
    )

    provider = FakeMarketDataProvider(
        assets=[
            Asset(
                symbol="SU.PA",
                name="Schneider Electric S.E.",
                exchange="Paris",
                currency="EUR",
            ),
            Asset(
                symbol="US80687P1066.SG",
                name="Schneider Electric SE (Unsp. AD)",
                exchange="Stuttgart",
                currency="EUR",
            ),
            Asset(
                symbol="SUN.MX",
                name="Schneider Electric S.E.",
                exchange="Mexico",
                currency="MXN",
            ),
        ]
    )

    resolver = AssetResolver(
        registry=registry,
        fallback_provider=provider,
    )

    with pytest.raises(
        AmbiguousAssetError,
        match="Several external assets",
    ):
        resolver.resolve("Schneider Electric")
