import pytest

from equity_strategist.universe_providers.euronext import (
    EuronextUniverseProvider,
)


def test_get_cac40_constituents() -> None:
    provider = EuronextUniverseProvider()

    constituents = provider.get_constituents("FR0003500008-XPAR")

    assert len(constituents) == 40

    assert constituents[0].name == "ACCOR"
    assert constituents[0].isin == "FR0000120404"

    assert any(
        constituent.name == "LVMH" and constituent.isin == "FR0000121014"
        for constituent in constituents
    )

    assert any(
        constituent.name == "HERMES INTL" and constituent.isin == "FR0000052292"
        for constituent in constituents
    )


def test_unknown_euronext_universe_fails() -> None:
    provider = EuronextUniverseProvider()

    with pytest.raises(
        ValueError,
        match="unsupported Euronext universe",
    ):
        provider.get_constituents("UNKNOWN")
