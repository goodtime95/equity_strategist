from typing import Any

import yfinance as yf

from equity_strategist.domain.models import Asset


class YahooFinanceProvider:
    """Market-data provider backed by Yahoo Finance."""

    def search_assets(self, query: str) -> list[Asset]:
        """Find assets matching a company name or ticker."""
        clean_query = query.strip()

        if not clean_query:
            return []

        search = yf.Search(
            clean_query,
            max_results=10,
            news_count=0,
        )

        assets: list[Asset] = []

        for quote in search.quotes:
            asset = self._quote_to_asset(quote)

            if asset is not None:
                assets.append(asset)

        return assets

    @staticmethod
    def _quote_to_asset(quote: dict[str, Any]) -> Asset | None:
        symbol = quote.get("symbol")

        if not symbol:
            return None

        quote_type = quote.get("quoteType")

        if quote_type not in {"EQUITY", "ETF", "INDEX"}:
            return None

        return Asset(
            symbol=symbol,
            name=quote.get("longname") or quote.get("shortname"),
            exchange=quote.get("exchDisp") or quote.get("exchange"),
            currency=quote.get("currency"),
        )
