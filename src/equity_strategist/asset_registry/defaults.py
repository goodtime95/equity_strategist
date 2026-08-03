from equity_strategist.asset_registry.registry import AssetRegistry
from equity_strategist.domain.asset import Asset

DEFAULT_ASSETS = [
    Asset(
        symbol="MC.PA",
        name="LVMH Moët Hennessy Louis Vuitton",
        exchange="Paris",
        currency="EUR",
        isin="FR0000121014",
        aliases=(
            "LVMH",
            "Louis Vuitton",
            "LVMH SE",
        ),
    ),
    Asset(
        symbol="RMS.PA",
        name="Hermès International",
        exchange="Paris",
        currency="EUR",
        isin="FR0000052292",
        aliases=(
            "Hermès",
            "Hermes",
            "Hermès International",
        ),
    ),
    Asset(
        symbol="ASML.AS",
        name="ASML Holding",
        exchange="Amsterdam",
        currency="EUR",
        isin="NL0010273215",
        aliases=(
            "ASML",
            "ASML Holding NV",
        ),
    ),
    Asset(
        symbol="NVDA",
        name="NVIDIA Corporation",
        exchange="Nasdaq",
        currency="USD",
        isin="US67066G1040",
        aliases=(
            "Nvidia",
            "NVIDIA",
        ),
    ),
    Asset(
        symbol="^FCHI",
        name="CAC 40",
        exchange="Paris",
        currency="EUR",
        aliases=(
            "CAC",
            "CAC40",
            "CAC 40",
        ),
    ),
    Asset(
        symbol="^STOXX50E",
        name="Euro Stoxx 50",
        exchange="Europe",
        currency="EUR",
        aliases=(
            "Eurostoxx 50",
            "Euro Stoxx",
            "SX5E",
        ),
    ),
    Asset(
        symbol="^GSPC",
        name="S&P 500",
        exchange="United States",
        currency="USD",
        aliases=(
            "SP500",
            "S&P500",
            "S&P 500",
        ),
    ),
]


def build_default_asset_registry() -> AssetRegistry:
    """Build the default registry used by the MVP."""

    return AssetRegistry(DEFAULT_ASSETS)
