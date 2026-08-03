import pytest

from equity_strategist.asset_registry.registry import AssetRegistry
from equity_strategist.domain.asset import Asset
from equity_strategist.tools.assets import AssetResolver
from equity_strategist.tools.exceptions import (
    AmbiguousAssetError,
    AssetNotFoundError,
)


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
