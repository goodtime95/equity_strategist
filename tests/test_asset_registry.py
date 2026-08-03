from equity_strategist.asset_registry.registry import AssetRegistry
from equity_strategist.domain.asset import Asset


def build_registry() -> AssetRegistry:
    return AssetRegistry(
        [
            Asset(
                symbol="MC.PA",
                name="LVMH Moët Hennessy Louis Vuitton",
                isin="FR0000121014",
                aliases=("LVMH", "Louis Vuitton"),
            ),
            Asset(
                symbol="RMS.PA",
                name="Hermès International",
                isin="FR0000052292",
                aliases=("Hermès", "Hermes"),
            ),
        ]
    )


def test_search_by_symbol() -> None:
    results = build_registry().search("MC.PA")

    assert len(results) == 1
    assert results[0].symbol == "MC.PA"


def test_search_by_isin() -> None:
    results = build_registry().search("FR0000052292")

    assert len(results) == 1
    assert results[0].symbol == "RMS.PA"


def test_search_by_alias_is_case_insensitive() -> None:
    results = build_registry().search("lvmh")

    assert len(results) == 1
    assert results[0].symbol == "MC.PA"


def test_search_supports_partial_names() -> None:
    results = build_registry().search("Hennessy")

    assert len(results) == 1
    assert results[0].symbol == "MC.PA"
