from datetime import date
from decimal import Decimal

from equity_strategist.domain.analysis_execution import (
    AnalysisExecutionResult,
)
from equity_strategist.domain.analysis_plan import (
    AnalysisPlan,
    Capability,
    PlanStep,
)
from equity_strategist.domain.analysis_request import (
    AnalysisIntent,
    AnalysisRequest,
)
from equity_strategist.domain.analysis_results import (
    VolatilityComparisonResult,
    VolatilityItem,
)
from equity_strategist.domain.asset import Asset
from equity_strategist.domain.results import PriceOnDateResult
from equity_strategist.strategists.executor import EquityExecutor


class FakeVolatilityAnalysisService:
    def compare(
        self,
        asset_queries: list[str],
        start_date: date,
        end_date: date,
        annualization_factor: int = 252,
        return_method=None,
    ) -> VolatilityComparisonResult:
        return VolatilityComparisonResult(
            start_date=start_date,
            end_date=end_date,
            annualization_factor=annualization_factor,
            items=(
                VolatilityItem(
                    symbol="MC.PA",
                    name="LVMH",
                    volatility=0.30,
                ),
                VolatilityItem(
                    symbol="RMS.PA",
                    name="Hermès",
                    volatility=0.25,
                ),
            ),
        )


class FakeMarketQueryService:
    def get_price_on_date(
        self,
        asset_query: str,
        target_date: date,
        preferred_exchange: str | None = None,
        preferred_currency: str | None = None,
        use_adjusted_close: bool = True,
    ) -> PriceOnDateResult:
        asset = Asset(
            symbol="MC.PA",
            name="LVMH",
            currency="EUR",
        )

        return PriceOnDateResult(
            asset=asset,
            requested_date=target_date,
            effective_date=target_date,
            price=Decimal("500.00"),
            price_type="adjusted_close",
            used_previous_session=False,
        )


def build_executor() -> EquityExecutor:
    return EquityExecutor(
        volatility_analysis_service=(FakeVolatilityAnalysisService()),
        market_query_service=FakeMarketQueryService(),
    )


def test_execute_volatility_plan() -> None:
    request = AnalysisRequest(
        intent=AnalysisIntent.COMPARE_VOLATILITY,
        assets=("LVMH", "Hermès"),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
    )

    plan = AnalysisPlan(
        request=request,
        steps=(PlanStep(capability=Capability.COMPARE_VOLATILITY),),
    )

    result = build_executor().execute(plan)

    assert isinstance(
        result,
        AnalysisExecutionResult,
    )
    assert len(result.step_results) == 1

    step_result = result.step_results[0]

    assert step_result.capability == Capability.COMPARE_VOLATILITY

    volatility_result = step_result.result

    assert isinstance(
        volatility_result,
        VolatilityComparisonResult,
    )
    assert len(volatility_result.items) == 2


def test_execute_price_on_date_plan() -> None:
    request = AnalysisRequest(
        intent=AnalysisIntent.PRICE_ON_DATE,
        assets=("LVMH",),
        target_date=date(2020, 3, 13),
    )

    plan = AnalysisPlan(
        request=request,
        steps=(PlanStep(capability=Capability.PRICE_ON_DATE),),
    )

    result = build_executor().execute(plan)

    price_result = result.step_results[0].result

    assert isinstance(
        price_result,
        PriceOnDateResult,
    )
    assert price_result.asset.symbol == "MC.PA"
    assert price_result.price == Decimal("500.00")
