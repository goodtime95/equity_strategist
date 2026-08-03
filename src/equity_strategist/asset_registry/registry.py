from equity_strategist.domain.asset import Asset


class AssetRegistry:
    """Internal registry of known financial assets."""

    def __init__(self, assets: list[Asset]) -> None:
        self._assets = tuple(assets)

    def search(self, query: str) -> list[Asset]:
        """Return registered assets matching a symbol, ISIN, name or alias."""
        clean_query = query.strip().casefold()

        if not clean_query:
            return []

        exact_matches = [
            asset for asset in self._assets if self._is_exact_match(asset, clean_query)
        ]

        if exact_matches:
            return exact_matches

        return [
            asset
            for asset in self._assets
            if self._is_partial_match(asset, clean_query)
        ]

    @staticmethod
    def _is_exact_match(
        asset: Asset,
        clean_query: str,
    ) -> bool:
        candidates = AssetRegistry._asset_search_terms(asset)

        return clean_query in candidates

    @staticmethod
    def _is_partial_match(
        asset: Asset,
        clean_query: str,
    ) -> bool:
        return any(
            clean_query in candidate
            for candidate in AssetRegistry._asset_search_terms(asset)
        )

    @staticmethod
    def _asset_search_terms(asset: Asset) -> set[str]:
        terms = {
            asset.symbol.casefold(),
        }

        if asset.name:
            terms.add(asset.name.casefold())

        if asset.isin:
            terms.add(asset.isin.casefold())

        terms.update(alias.casefold() for alias in asset.aliases)

        return terms
