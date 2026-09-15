import re
from datetime import date, timedelta

from equity_strategist.domain.analysis_request import (
    AnalysisHorizon,
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
    PerformanceMeasure,
    RankingDirection,
)
from equity_strategist.universe_registry.registry import (
    UniverseRegistry,
)


class UnderstandingError(ValueError):
    """Raised when a user question cannot be parsed reliably."""


class RuleBasedUnderstanding:
    """Temporary deterministic natural-language understanding layer."""

    def __init__(
        self,
        universe_registry: UniverseRegistry,
    ) -> None:
        self.universe_registry = universe_registry

    def understand(
        self,
        question: str,
        today: date | None = None,
    ) -> AnalysisRequest:
        clean_question = question.strip()

        if not clean_question:
            raise UnderstandingError("question cannot be empty")

        reference_date = today or date.today()

        objective = self._parse_objective(clean_question)
        metrics = self._parse_metrics(clean_question)
        universe = self._parse_universe(clean_question)
        assets = self._parse_assets(
            clean_question,
            required=universe is None,
        )

        start_date, end_date = self._parse_period(
            clean_question,
            reference_date,
        )

        target_date = self._parse_target_date(clean_question)
        ranking_direction = (
            self._parse_ranking_direction(clean_question)
            if objective == AnalysisObjective.RANK
            else None
        )
        top_n = (
            self._parse_top_n(clean_question)
            if objective == AnalysisObjective.RANK
            else None
        )
        horizons = self._parse_horizons(clean_question)
        if horizons:
            start_date = None
            end_date = reference_date
        benchmark = self._parse_benchmark(clean_question)

        return AnalysisRequest(
            objective=objective,
            metrics=metrics,
            assets=assets,
            universe=universe,
            start_date=start_date,
            end_date=end_date,
            target_date=target_date,
            benchmark=benchmark,
            ranking_direction=ranking_direction,
            top_n=top_n,
            performance_measure=self._parse_performance_measure(clean_question),
            horizons=horizons,
            user_context=clean_question,
        )

    @staticmethod
    def _parse_objective(
        question: str,
    ) -> AnalysisObjective:
        lower = question.casefold()

        rank_words = (
            "classe",
            "classement",
            "rank",
            "ranking",
            "top",
            "bottom",
            "best",
            "worst",
            "highest",
            "lowest",
            "most",
            "least",
            "meilleures",
            "meilleurs",
            "pires",
            "plus faible",
            "moins volatil",
        )

        if any(word in lower for word in rank_words):
            return AnalysisObjective.RANK

        compare_words = (
            "compare",
            "comparaison",
            "versus",
            " vs ",
        )

        if any(word in lower for word in compare_words):
            return AnalysisObjective.COMPARE

        get_words = (
            "quel était",
            "quelle était",
            "quel est",
            "quelle est",
            "donne",
            "prix de",
        )

        if any(word in lower for word in get_words):
            return AnalysisObjective.GET

        analyze_words = (
            "analyse",
            "analyze",
        )

        if any(word in lower for word in analyze_words):
            return AnalysisObjective.ANALYZE

        raise UnderstandingError("unable to identify analysis objective")

    @staticmethod
    def _parse_metrics(
        question: str,
    ) -> tuple[AnalysisMetric, ...]:
        lower = question.casefold()

        metrics: list[AnalysisMetric] = []

        if "volatil" in lower or " vol " in lower:
            metrics.append(AnalysisMetric.VOLATILITY)

        if "performance" in lower or "perf " in lower:
            metrics.append(AnalysisMetric.PERFORMANCE)

        if "corrél" in lower or "correl" in lower:
            metrics.append(AnalysisMetric.CORRELATION)

        if "drawdown" in lower:
            metrics.append(AnalysisMetric.DRAWDOWN)

        if "prix" in lower or "price" in lower:
            metrics.append(AnalysisMetric.PRICE)

        if not metrics:
            raise UnderstandingError("unable to identify requested metric")

        return tuple(metrics)

    @staticmethod
    def _parse_assets(
        question: str,
        required: bool = True,
    ) -> tuple[str, ...]:
        known_assets = (
            "LVMH",
            "Hermès",
            "Hermes",
            "ASML",
            "Nvidia",
            "NVIDIA",
        )

        found: list[str] = []

        lower = question.casefold()

        for asset in known_assets:
            if asset.casefold() in lower:
                canonical = (
                    "Hermès"
                    if asset in {"Hermès", "Hermes"}
                    else "Nvidia"
                    if asset in {"Nvidia", "NVIDIA"}
                    else asset
                )

                if canonical not in found:
                    found.append(canonical)

        if not found and required:
            raise UnderstandingError("unable to identify requested assets")

        return tuple(found)

    @staticmethod
    def _parse_period(
        question: str,
        today: date,
    ) -> tuple[date | None, date | None]:
        lower = question.casefold()

        match = re.search(
            r"(?:sur|over)\s+(?:les\s+)?(\d+)\s+"
            r"(?:dernières?\s+)?années?",
            lower,
        )

        if match:
            years = int(match.group(1))

            try:
                start_date = today.replace(year=today.year - years)
            except ValueError:
                start_date = today - timedelta(days=365 * years)

            return start_date, today

        match = re.search(
            r"depuis\s+(\d{4})",
            lower,
        )

        if match:
            year = int(match.group(1))
            return date(year, 1, 1), today

        return None, None

    @staticmethod
    def _parse_target_date(
        question: str,
    ) -> date | None:
        match = re.search(
            r"\b(\d{4})-(\d{2})-(\d{2})\b",
            question,
        )

        if not match:
            return None

        year, month, day = (int(value) for value in match.groups())

        return date(year, month, day)

    @staticmethod
    def _parse_ranking_direction(question: str) -> RankingDirection:
        lower = question.casefold()
        lowest_words = (
            "least",
            "lowest",
            "bottom",
            "worst",
            "moins volatil",
            "moins performant",
            "plus faible",
            "pires",
        )

        if any(word in lower for word in lowest_words):
            return RankingDirection.LOWEST

        return RankingDirection.HIGHEST

    @staticmethod
    def _parse_top_n(question: str) -> int | None:
        match = re.search(r"\btop\s+(\d+)\b", question, flags=re.IGNORECASE)

        if match is None:
            return None

        return int(match.group(1))

    @staticmethod
    def _parse_horizons(question: str) -> tuple[AnalysisHorizon, ...]:
        lower = question.casefold()
        mappings = (
            (r"\bytd\b|year[- ]to[- ]date", AnalysisHorizon.YEAR_TO_DATE),
            (r"\b1m\b", AnalysisHorizon.ONE_MONTH),
            (r"\b3m\b", AnalysisHorizon.THREE_MONTHS),
            (r"\b6m\b", AnalysisHorizon.SIX_MONTHS),
            (r"\b1y\b", AnalysisHorizon.ONE_YEAR),
            (r"\b3y\b", AnalysisHorizon.THREE_YEARS),
        )
        return tuple(
            horizon for pattern, horizon in mappings if re.search(pattern, lower)
        )

    @staticmethod
    def _parse_performance_measure(question: str) -> PerformanceMeasure:
        lower = question.casefold()
        if "annualized" in lower or "annualised" in lower or "annualisée" in lower:
            return PerformanceMeasure.ANNUALIZED
        if "excess return" in lower or "surperformance" in lower:
            return PerformanceMeasure.EXCESS_RETURN
        if "relative performance" in lower or "performance relative" in lower:
            return PerformanceMeasure.RELATIVE
        return PerformanceMeasure.TOTAL

    @staticmethod
    def _parse_benchmark(question: str) -> str | None:
        lower = question.casefold()
        if not any(
            marker in lower
            for marker in ("benchmark", "relative to", "relative à", "excess")
        ):
            return None
        for name in ("S&P 500", "CAC 40", "Euro Stoxx 50"):
            if name.casefold() in lower:
                return name
        return None

    def _parse_universe(
        self,
        question: str,
    ) -> str | None:
        lower = question.casefold()

        for universe in self.universe_registry.universes:
            terms = (
                universe.name,
                *universe.aliases,
            )

            for term in terms:
                if term.casefold() in lower:
                    return universe.name

        return None
