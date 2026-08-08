from datetime import date

from equity_strategist.compute.returns import (
    ReturnMethod,
    compute_returns,
)
from equity_strategist.compute.volatility import compute_volatility
from equity_strategist.domain.analysis_results import (
    VolatilityComparisonResult,
    VolatilityItem,
)
from equity_strategist.services.market_series import MarketSeriesService


class VolatilityAnalysisService:
    """Compare historical volatility across several assets."""

    def __init__(
        self,
        market_series_service: MarketSeriesService,
    ) -> None:
        self.market_series_service = market_series_service

    def compare(
        self,
        asset_queries: list[str],
        start_date: date,
        end_date: date,
        annualization_factor: int = 252,
        return_method: ReturnMethod = ReturnMethod.LOG,
    ) -> VolatilityComparisonResult:
        """Compare annualized volatility across several assets."""
        if len(asset_queries) < 2:
            raise ValueError("at least two assets are required for comparison")

        items: list[VolatilityItem] = []

        for asset_query in asset_queries:
            price_series = self.market_series_service.get_price_series(
                asset_query=asset_query,
                start_date=start_date,
                end_date=end_date,
            )

            return_series = compute_returns(
                price_series=price_series,
                method=return_method,
            )

            volatility = compute_volatility(
                return_series=return_series,
                annualization_factor=annualization_factor,
            )

            asset = price_series.metadata["asset"]

            items.append(
                VolatilityItem(
                    symbol=asset.symbol,
                    name=asset.name,
                    volatility=volatility,
                )
            )

        ranked_items = tuple(
            sorted(
                items,
                key=lambda item: item.volatility,
                reverse=True,
            )
        )

        return VolatilityComparisonResult(
            start_date=start_date,
            end_date=end_date,
            annualization_factor=annualization_factor,
            items=ranked_items,
        )
