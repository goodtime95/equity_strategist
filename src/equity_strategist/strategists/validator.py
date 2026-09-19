from equity_strategist.domain.analysis_plan import Capability
from equity_strategist.domain.analysis_request import (
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
    PerformanceMeasure,
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
                issues=tuple(message for _, message in clarification_issues),
                issue_codes=tuple(code for code, _ in clarification_issues),
            )

        unsupported_issues = self._find_unsupported_issues(request)

        if unsupported_issues:
            return RequestValidationResult(
                status=RequestStatus.UNSUPPORTED,
                issues=tuple(message for _, message in unsupported_issues),
                issue_codes=tuple(code for code, _ in unsupported_issues),
            )

        return RequestValidationResult(
            status=RequestStatus.READY,
        )

    def _find_clarification_issues(
        self,
        request: AnalysisRequest,
    ) -> list[tuple[str, str]]:
        issues = [("unresolved_semantics", message) for message in request.unresolved]

        blank_asset_queries = [asset for asset in request.assets if not asset.strip()]
        normalized_asset_queries = [
            asset.strip().casefold() for asset in request.assets if asset.strip()
        ]

        if not request.assets and request.universe is None:
            issues.append(
                ("missing_asset_source", "at least one asset or universe is required")
            )

        if request.assets and request.universe is not None:
            issues.append(
                (
                    "conflicting_asset_sources",
                    "assets and universe cannot both be used; specify one asset source",
                )
            )

        if blank_asset_queries:
            issues.append(
                (
                    "blank_asset",
                    "asset queries cannot be blank; provide an asset name or symbol",
                )
            )

        if len(normalized_asset_queries) != len(set(normalized_asset_queries)):
            issues.append(
                (
                    "duplicate_asset",
                    "duplicate asset queries are not allowed; specify distinct assets",
                )
            )

        if request.universe is not None and not request.universe.strip():
            issues.append(
                (
                    "blank_universe",
                    "universe cannot be blank; provide a named investment universe",
                )
            )

        if not request.metrics:
            issues.append(
                ("missing_metric", "at least one analysis metric is required")
            )

        non_performance_period_metrics = any(
            metric in self.PERIOD_METRICS and metric != AnalysisMetric.PERFORMANCE
            for metric in request.metrics
        )

        if request.horizons:
            if request.start_date is not None:
                issues.append(
                    (
                        "horizon_start_conflict",
                        "horizon requests must not include start_date; use end_date as "
                        "the anchor",
                    )
                )
            if request.end_date is None:
                issues.append(
                    (
                        "missing_horizon_anchor",
                        "end date is required for horizon requests",
                    )
                )
            if non_performance_period_metrics:
                issues.append(
                    (
                        "mixed_horizon_metrics",
                        "performance horizons cannot currently be combined with other "
                        "period metrics; use an explicit period",
                    )
                )
        elif any(metric in self.PERIOD_METRICS for metric in request.metrics):
            if request.start_date is None:
                issues.append(("missing_start_date", "start date is required"))

            if request.end_date is None:
                issues.append(("missing_end_date", "end date is required"))

        if (
            request.performance_measure
            in {
                PerformanceMeasure.RELATIVE,
                PerformanceMeasure.EXCESS_RETURN,
            }
            and request.benchmark is None
        ):
            issues.append(
                (
                    "missing_benchmark",
                    f"{request.performance_measure.value} requires a benchmark",
                )
            )

        if request.benchmark is not None and not request.benchmark.strip():
            issues.append(
                (
                    "blank_benchmark",
                    "benchmark cannot be blank; provide an asset or index",
                )
            )

        if AnalysisMetric.PRICE in request.metrics:
            if request.target_date is None:
                issues.append(
                    ("missing_target_date", "target date is required for price queries")
                )

            if request.objective == AnalysisObjective.GET and len(request.assets) != 1:
                issues.append(
                    (
                        "price_asset_count",
                        "price queries require exactly one asset; "
                        "specify a single asset",
                    )
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
                (
                    "comparison_asset_count",
                    "comparison and ranking requests with explicit assets require at "
                    "least two assets; specify another asset",
                )
            )

        if (
            AnalysisMetric.CORRELATION in request.metrics
            and request.assets
            and len(request.assets) < 2
        ):
            issues.append(
                ("correlation_asset_count", "correlation requires at least two assets")
            )

        return issues

    @staticmethod
    def _find_unsupported_issues(
        request: AnalysisRequest,
    ) -> list[tuple[str, str]]:
        issues: list[tuple[str, str]] = []

        has_performance = AnalysisMetric.PERFORMANCE in request.metrics

        if request.benchmark is not None and not has_performance:
            issues.append(
                (
                    "benchmark_metric_unsupported",
                    "benchmark is only supported for performance analysis",
                )
            )

        if request.horizons and not has_performance:
            issues.append(
                (
                    "horizon_metric_unsupported",
                    "horizons are only supported for performance analysis",
                )
            )

        if (
            request.performance_measure != PerformanceMeasure.TOTAL
            and not has_performance
        ):
            issues.append(
                (
                    "performance_measure_metric_unsupported",
                    "performance_measure is only supported for performance analysis",
                )
            )

        if request.constraints:
            issues.append(
                (
                    "constraints_unsupported",
                    "request constraints are not currently supported",
                )
            )

        if request.market_period is not None:
            issues.append(
                (
                    "market_period_unsupported",
                    "market_period is not currently supported; use explicit dates",
                )
            )

        if request.objective != AnalysisObjective.RANK:
            if request.ranking_direction is not None:
                issues.append(
                    (
                        "ranking_direction_unsupported",
                        "ranking_direction is only supported for rank requests",
                    )
                )

            if request.top_n is not None:
                issues.append(
                    ("top_n_unsupported", "top_n is only supported for rank requests")
                )

        if (
            request.target_date is not None
            and AnalysisMetric.PRICE not in request.metrics
        ):
            issues.append(
                (
                    "target_date_unsupported",
                    "target_date is only supported for price requests",
                )
            )

        if (
            (request.start_date is not None or request.end_date is not None)
            and not any(
                metric in AnalysisRequestValidator.PERIOD_METRICS
                for metric in request.metrics
            )
            and not request.horizons
        ):
            issues.append(
                (
                    "period_dates_unsupported",
                    "start_date and end_date are only supported "
                    "for period-based metrics",
                )
            )

        for metric in request.metrics:
            capability = EquityPlanner.CAPABILITY_MAP.get(
                (
                    request.objective,
                    metric,
                )
            )

            if capability is None:
                issues.append(
                    (
                        "analysis_combination_unsupported",
                        "unsupported analysis combination: "
                        f"{request.objective.value} + "
                        f"{metric.value}",
                    )
                )

                continue

            if (
                request.universe is not None
                and capability not in AnalysisRequestValidator.UNIVERSE_CAPABILITIES
            ):
                issues.append(
                    (
                        "universe_capability_unsupported",
                        "capability does not currently support universes: "
                        f"{capability.value}",
                    )
                )

        return issues
