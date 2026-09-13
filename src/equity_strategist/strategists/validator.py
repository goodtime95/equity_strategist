from equity_strategist.domain.analysis_plan import Capability
from equity_strategist.domain.analysis_request import (
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
)
from equity_strategist.domain.request_validation import (
    RequestStatus,
    RequestValidationResult,
)
from equity_strategist.strategists.planner import EquityPlanner


class AnalysisRequestValidator:
    """Decide whether a structured analysis request can be executed."""

    PERIOD_METRICS = {
        AnalysisMetric.PERFORMANCE,
        AnalysisMetric.VOLATILITY,
        AnalysisMetric.CORRELATION,
        AnalysisMetric.DRAWDOWN,
    }

    UNIVERSE_CAPABILITIES = {
        Capability.RANK_PERFORMANCE,
    }

    def validate(
        self,
        request: AnalysisRequest,
    ) -> RequestValidationResult:
        clarification_issues = self._find_clarification_issues(request)

        if clarification_issues:
            return RequestValidationResult(
                status=RequestStatus.NEEDS_CLARIFICATION,
                issues=tuple(clarification_issues),
            )

        unsupported_issues = self._find_unsupported_issues(request)

        if unsupported_issues:
            return RequestValidationResult(
                status=RequestStatus.UNSUPPORTED,
                issues=tuple(unsupported_issues),
            )

        return RequestValidationResult(
            status=RequestStatus.READY,
        )

    def _find_clarification_issues(
        self,
        request: AnalysisRequest,
    ) -> list[str]:
        issues = list(request.unresolved)

        blank_asset_queries = [asset for asset in request.assets if not asset.strip()]
        normalized_asset_queries = [
            asset.strip().casefold() for asset in request.assets if asset.strip()
        ]

        if not request.assets and request.universe is None:
            issues.append("at least one asset or universe is required")

        if blank_asset_queries:
            issues.append(
                "asset queries cannot be blank; provide an asset name or symbol"
            )

        if len(normalized_asset_queries) != len(set(normalized_asset_queries)):
            issues.append(
                "duplicate asset queries are not allowed; specify distinct assets"
            )

        if request.universe is not None and not request.universe.strip():
            issues.append(
                "universe cannot be blank; provide a named investment universe"
            )

        if not request.metrics:
            issues.append("at least one analysis metric is required")

        if any(metric in self.PERIOD_METRICS for metric in request.metrics):
            if request.start_date is None:
                issues.append("start date is required")

            if request.end_date is None:
                issues.append("end date is required")

        if AnalysisMetric.PRICE in request.metrics:
            if request.target_date is None:
                issues.append("target date is required for price queries")

            if request.objective == AnalysisObjective.GET and len(request.assets) != 1:
                issues.append(
                    "price queries require exactly one asset; specify a single asset"
                )

        if (
            request.objective
            in {
                AnalysisObjective.COMPARE,
                AnalysisObjective.RANK,
            }
            and request.assets
            and len(request.assets) < 2
        ):
            issues.append(
                "comparison and ranking requests with explicit assets require at "
                "least two assets; specify another asset"
            )

        if (
            AnalysisMetric.CORRELATION in request.metrics
            and request.assets
            and len(request.assets) < 2
        ):
            issues.append("correlation requires at least two assets")

        return issues

    @staticmethod
    def _find_unsupported_issues(
        request: AnalysisRequest,
    ) -> list[str]:
        issues: list[str] = []

        for metric in request.metrics:
            capability = EquityPlanner.CAPABILITY_MAP.get(
                (
                    request.objective,
                    metric,
                )
            )

            if capability is None:
                issues.append(
                    "unsupported analysis combination: "
                    f"{request.objective.value} + "
                    f"{metric.value}"
                )

                continue

            if (
                request.universe is not None
                and capability not in AnalysisRequestValidator.UNIVERSE_CAPABILITIES
            ):
                issues.append(
                    "capability does not currently support universes: "
                    f"{capability.value}"
                )

        return issues
