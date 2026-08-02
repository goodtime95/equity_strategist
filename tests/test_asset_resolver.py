from datetime import date

import pytest

from equity_strategist.domain.models import Asset, PriceBar
from equity_strategist.tools.assets import AssetResolver
from equity_strategist.tools.exceptions import (
    AmbiguousAssetError,
    AssetNotFoundError,
)


class FakeMarketDataProvider:
    def __init__(self, assets: list[Asset]) -> None:
        self.assets = assets

    def search_assets(self, query: str) -> list[Asset]:
        return self.assets

    def get_daily_prices(
        self,
        asset: Asset,
        start_date: date,
        end_date: date,
    ) -> list[PriceBar]:
        return []


def test_resolve_exact_symbol() -> None:
    provider = FakeMarketDataProvider(
        [
            Asset(
                symbol="LVMUY",
                name="LVMH ADR",
                currency="USD",
            ),
            Asset(
                symbol="MC.PA",
                name="LVMH",
                currency="EUR",
            ),
        ]
    )

    resolver = AssetResolver(provider)

    result = resolver.resolve("MC.PA")

    assert result.symbol == "MC.PA"


def test_resolve_using_preferred_currency() -> None:
    provider = FakeMarketDataProvider(
        [
            Asset(
                symbol="LVMUY",
                name="LVMH ADR",
                currency="USD",
            ),
            Asset(
                symbol="MC.PA",
                name="LVMH",
                currency="EUR",
            ),
        ]
    )

    resolver = AssetResolver(provider)

    result = resolver.resolve(
        "LVMH",
        preferred_currency="EUR",
    )

    assert result.symbol == "MC.PA"


def test_resolve_raises_when_no_asset_is_found() -> None:
    resolver = AssetResolver(FakeMarketDataProvider([]))

    with pytest.raises(AssetNotFoundError):
        resolver.resolve("Unknown company")


def test_resolve_raises_when_query_is_ambiguous() -> None:
    provider = FakeMarketDataProvider(
        [
            Asset(symbol="ABC.PA", name="ABC", currency="EUR"),
            Asset(symbol="ABC.L", name="ABC", currency="GBP"),
        ]
    )

    resolver = AssetResolver(provider)

    with pytest.raises(AmbiguousAssetError):
        resolver.resolve("ABC")


def test_resolve_using_preferred_exchange() -> None:
    provider = FakeMarketDataProvider(
        [
            Asset(
                symbol="LVMUY",
                name="LVMH ADR",
                exchange="OTC Markets",
                currency="USD",
            ),
            Asset(
                symbol="MC.PA",
                name="LVMH",
                exchange="Paris",
                currency="EUR",
            ),
        ]
    )

    resolver = AssetResolver(provider)

    result = resolver.resolve(
        "LVMH",
        preferred_exchange="Paris",
    )

    assert result.symbol == "MC.PA"
