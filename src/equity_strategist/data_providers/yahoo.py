from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pandas as pd
import yfinance as yf

from equity_strategist.domain.asset import Asset
from equity_strategist.domain.observations import DailyPriceObservation


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

    def get_daily_prices(
        self,
        asset: Asset,
        start_date: date,
        end_date: date,
    ) -> list[DailyPriceObservation]:
        """Return daily OHLCV data over an inclusive interval."""
        if start_date > end_date:
            raise ValueError("start_date must be before or equal to end_date")

        ticker = yf.Ticker(asset.symbol)

        history = ticker.history(
            start=start_date.isoformat(),
            end=(end_date + timedelta(days=1)).isoformat(),
            interval="1d",
            auto_adjust=False,
            actions=False,
            raise_errors=True,
        )

        if history.empty:
            return []

        return [
            self._row_to_observation(asset, index, row)
            for index, row in history.iterrows()
        ]

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

    @staticmethod
    def _row_to_observation(
        asset: Asset,
        index: Any,
        row: pd.Series,
    ) -> DailyPriceObservation:
        adjusted_close = row.get("Adj Close")
        volume = row.get("Volume")

        return DailyPriceObservation(
            asset=asset,
            date=index.date(),
            open=Decimal(str(row["Open"])),
            high=Decimal(str(row["High"])),
            low=Decimal(str(row["Low"])),
            close=Decimal(str(row["Close"])),
            adjusted_close=(
                None
                if adjusted_close is None or pd.isna(adjusted_close)
                else Decimal(str(adjusted_close))
            ),
            volume=(None if volume is None or pd.isna(volume) else int(volume)),
        )
