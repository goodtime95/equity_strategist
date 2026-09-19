import json
from datetime import date

from openai import APIError, OpenAI

from equity_strategist.domain.analysis_request import (
    AnalysisHorizon,
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
    PerformanceMeasure,
    RankingDirection,
)
from equity_strategist.domain.errors import ProviderFailure

ANALYSIS_REQUEST_SCHEMA = {
    "type": "object",
    "properties": {
        "objective": {
            "type": "string",
            "enum": [
                "get",
                "compare",
                "rank",
                "analyze",
            ],
        },
        "metrics": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "price",
                    "performance",
                    "volatility",
                    "correlation",
                    "drawdown",
                ],
            },
        },
        "assets": {
            "type": "array",
            "description": (
                "Explicit asset references named by the user, including when "
                "the user also names a universe."
            ),
            "items": {
                "type": "string",
            },
        },
        "universe": {
            "type": ["string", "null"],
            "description": (
                "Explicit investment universe named by the user, including when "
                "the user also names individual assets."
            ),
        },
        "start_date": {
            "type": ["string", "null"],
        },
        "end_date": {
            "type": ["string", "null"],
        },
        "target_date": {
            "type": ["string", "null"],
        },
        "benchmark": {
            "type": ["string", "null"],
        },
        "constraints": {
            "type": "array",
            "description": (
                "Additional analytical restrictions not represented by any other "
                "request field. Metric and ordinary price wording do not belong here."
            ),
            "items": {
                "type": "string",
            },
        },
        "ranking_direction": {
            "type": ["string", "null"],
            "enum": ["highest", "lowest", None],
            "description": (
                "Explicit ordering direction requested by the user. Null for a "
                "generic rank request with no stated direction."
            ),
        },
        "top_n": {
            "type": ["integer", "null"],
            "minimum": 1,
        },
        "performance_measure": {
            "type": "string",
            "enum": ["total", "annualized", "relative", "excess_return"],
            "description": (
                "Benchmark presence alone does not change the measure. Use total "
                "unless annualized, relative performance, or excess return is "
                "explicitly requested."
            ),
        },
        "horizons": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["1m", "3m", "6m", "ytd", "1y", "3y"],
            },
        },
        "unresolved": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
    },
    "required": [
        "objective",
        "metrics",
        "assets",
        "universe",
        "start_date",
        "end_date",
        "target_date",
        "benchmark",
        "constraints",
        "ranking_direction",
        "top_n",
        "performance_measure",
        "horizons",
        "unresolved",
    ],
    "additionalProperties": False,
}


class LLMUnderstanding:
    """Use an LLM to convert natural language into an AnalysisRequest."""

    def __init__(
        self,
        client: OpenAI | None = None,
        model: str = "gpt-5.6",
    ) -> None:
        self.client = client or OpenAI()
        self.model = model

    def understand(
        self,
        question: str,
    ) -> AnalysisRequest:
        if not question.strip():
            raise ValueError("question cannot be empty")

        today = date.today()

        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=self._build_instructions(today),
                input=question,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "equity_analysis_request",
                        "strict": True,
                        "schema": ANALYSIS_REQUEST_SCHEMA,
                    }
                },
            )
        except APIError as error:
            raise ProviderFailure("External provider call failed") from error

        payload = json.loads(response.output_text)

        return AnalysisRequest(
            objective=AnalysisObjective(payload["objective"]),
            metrics=tuple(AnalysisMetric(metric) for metric in payload["metrics"]),
            assets=tuple(payload["assets"]),
            universe=payload["universe"],
            start_date=self._parse_date(payload["start_date"]),
            end_date=self._parse_date(payload["end_date"]),
            target_date=self._parse_date(payload["target_date"]),
            benchmark=payload["benchmark"],
            constraints=tuple(payload["constraints"]),
            ranking_direction=(
                RankingDirection(payload["ranking_direction"])
                if payload["ranking_direction"] is not None
                else None
            ),
            top_n=payload["top_n"],
            performance_measure=PerformanceMeasure(
                payload.get("performance_measure", PerformanceMeasure.TOTAL.value)
            ),
            horizons=tuple(
                AnalysisHorizon(horizon) for horizon in payload.get("horizons", [])
            ),
            user_context=question,
            unresolved=tuple(payload["unresolved"]),
        )

    def refine(
        self,
        previous_request: AnalysisRequest,
        clarification: str,
    ) -> AnalysisRequest:
        if not clarification.strip():
            raise ValueError("clarification cannot be empty")

        today = date.today()

        previous_request_payload = {
            "objective": previous_request.objective.value,
            "metrics": [metric.value for metric in previous_request.metrics],
            "assets": list(previous_request.assets),
            "universe": previous_request.universe,
            "start_date": (
                previous_request.start_date.isoformat()
                if previous_request.start_date is not None
                else None
            ),
            "end_date": (
                previous_request.end_date.isoformat()
                if previous_request.end_date is not None
                else None
            ),
            "target_date": (
                previous_request.target_date.isoformat()
                if previous_request.target_date is not None
                else None
            ),
            "benchmark": previous_request.benchmark,
            "constraints": list(previous_request.constraints),
            "ranking_direction": (
                previous_request.ranking_direction.value
                if previous_request.ranking_direction is not None
                else None
            ),
            "top_n": previous_request.top_n,
            "performance_measure": previous_request.performance_measure.value,
            "horizons": [horizon.value for horizon in previous_request.horizons],
            "unresolved": list(previous_request.unresolved),
        }

        input_payload = {
            "previous_request": previous_request_payload,
            "clarification": clarification,
        }

        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=self._build_refinement_instructions(today),
                input=json.dumps(
                    input_payload,
                    ensure_ascii=False,
                ),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "equity_analysis_request",
                        "strict": True,
                        "schema": ANALYSIS_REQUEST_SCHEMA,
                    }
                },
            )
        except APIError as error:
            raise ProviderFailure("External provider call failed") from error

        payload = json.loads(response.output_text)

        return AnalysisRequest(
            objective=AnalysisObjective(payload["objective"]),
            metrics=tuple(AnalysisMetric(metric) for metric in payload["metrics"]),
            assets=tuple(payload["assets"]),
            universe=payload["universe"],
            start_date=self._parse_date(payload["start_date"]),
            end_date=self._parse_date(payload["end_date"]),
            target_date=self._parse_date(payload["target_date"]),
            benchmark=payload["benchmark"],
            constraints=tuple(payload["constraints"]),
            ranking_direction=(
                RankingDirection(payload["ranking_direction"])
                if payload["ranking_direction"] is not None
                else None
            ),
            top_n=payload["top_n"],
            performance_measure=PerformanceMeasure(
                payload.get("performance_measure", PerformanceMeasure.TOTAL.value)
            ),
            horizons=tuple(
                AnalysisHorizon(horizon) for horizon in payload.get("horizons", [])
            ),
            user_context=clarification,
            unresolved=tuple(payload["unresolved"]),
        )

    @staticmethod
    def _parse_date(
        value: str | None,
    ) -> date | None:
        if value is None:
            return None

        return date.fromisoformat(value)

    @staticmethod
    def _build_instructions(
        today: date,
    ) -> str:
        return f"""
You are the understanding layer of an equity quantitative
analysis system.

Your only task is to convert the user's question into a
structured analysis request.

Today is {today.isoformat()}.

Supported objectives:
- get
- compare
- rank
- analyze

Supported metrics:
- price
- performance
- volatility
- correlation
- drawdown

Rules:

1. Extract company names, tickers, indices or other asset
   references exactly enough for a downstream asset resolver.

2. Do not perform financial calculations.

3. Do not answer the user's question.

4. Resolve relative dates using today's date.

5. Use ISO dates YYYY-MM-DD.

6. If the user asks for several metrics, return all of them.

7. Extract explicit assets and an explicit investment universe independently.
   If the user names both, populate both assets and universe. Leave assets empty
   only when the user names a universe without naming individual assets.

8. If information is ambiguous or missing, record a concise
   description in unresolved.

9. Do not invent an asset, date, benchmark or universe.

10. "risk" alone should not automatically be interpreted as
    volatility unless the question clearly implies historical
    volatility.

11. Set ranking_direction only when the user explicitly communicates an ordering
    direction. Use "highest" for best, highest, most, top, or "from highest to
    lowest" requests. Use "lowest" for worst, lowest, least, bottom, or "from
    lowest to highest" requests. A generic request to rank assets by a metric does
    not specify direction: leave ranking_direction null. Do not infer "highest"
    merely because objective = rank. Extract an explicit top-N limit into top_n.

12. Leave ranking_direction and top_n null for non-ranking requests.

13. Preserve any requested benchmark in benchmark. Naming a benchmark does not
    itself request relative performance or excess return. For total or annualized
    performance, preserve the benchmark so its own performance is calculated and
    exposed alongside the asset results.

14. Put only genuine additional analytical restrictions that are not already
    represented by another AnalysisRequest field in constraints. Examples include
    "EUR only" and explicit analytical filters with no dedicated field.

15. Do not put objective, metric, asset, universe, date, benchmark, ranking
    direction, or top-N wording in constraints. In particular:
    - "maximum drawdown" means metric = drawdown;
    - "historical volatility" means metric = volatility;
    - "performance" means metric = performance;
    - "closing price" or "close price" means metric = price.
    These phrases are not constraints. The downstream engine's standard price
    convention remains authoritative; do not create a price-type constraint or
    unresolved item.

16. For performance, set performance_measure to total unless the user explicitly
    requests annualized performance, relative performance, or excess return.
    A comparison "with", "against", or "versus" a benchmark alone remains total
    performance; it does not request a relative-wealth calculation. Use relative
    only for explicit relative performance. Use excess_return for an explicit
    return difference or outperformance in return terms. Preserve the reference
    asset or index in benchmark independently of performance_measure.

17. Extract explicit standard performance horizons as one or more of 1m, 3m,
    6m, ytd, 1y, and 3y. For horizon requests set start_date to null and resolve
    end_date to the requested anchor date, or today when no other anchor is given.
    For an explicit date interval leave horizons empty.

Objective selection rules:

- Use "get" when the user requests a specific value or observation.

- Use "compare" when the user wants metrics compared across assets
  but does not explicitly ask for an ordering or winner.

- Use "rank" when the user asks which asset is best, worst, highest,
  lowest, most, least, top, bottom, or otherwise requests an ordering.

Examples:
"Compare the performance of LVMH and Hermes"
-> compare

"Which of LVMH and Hermes performed best?"
-> rank

"Which stock was the least volatile?"
-> rank

Ranking direction examples:

"Rank LVMH, SAP and Siemens by performance"
-> ranking_direction = null

"Rank LVMH, SAP and Siemens from highest to lowest performance"
-> ranking_direction = highest

"Which of LVMH and SAP performed best?"
-> ranking_direction = highest

"Show the top 3 performers"
-> ranking_direction = highest, top_n = 3

"Which stock was least volatile?"
-> ranking_direction = lowest

"Show the bottom 5 performers"
-> ranking_direction = lowest, top_n = 5

Performance measure examples:

"Compare LVMH performance with the Euro Stoxx 50 as benchmark"
-> performance_measure = total, benchmark = "Euro Stoxx 50"

"Show LVMH annualized performance versus the Euro Stoxx 50 benchmark"
-> performance_measure = annualized, benchmark = "Euro Stoxx 50"

"What is LVMH's relative performance versus the Euro Stoxx 50?"
-> performance_measure = relative, benchmark = "Euro Stoxx 50"

"How much did LVMH outperform the Euro Stoxx 50 in return terms?"
-> performance_measure = excess_return, benchmark = "Euro Stoxx 50"

Examples:

"Compare LVMH and Hermes over the last 2 years in performance
and volatility"
means:
objective = compare
metrics = performance, volatility

"Rank Nvidia, ASML and LVMH by performance since 2024"
means:
objective = rank
metrics = performance

"What was LVMH's price on 2020-03-15?"
means:
objective = get
metrics = price
target_date = 2020-03-15

Unresolved information rules:

The understanding layer decides WHAT the user wants analyzed.
The quantitative engine decides HOW the calculation is performed.

Do not mark implementation or quantitative conventions as unresolved
when the downstream engine can apply its standard methodology.

Do not ask the user to specify:
- return calculation method,
- annualization factor,
- standard correlation methodology,
- standard historical volatility methodology,
- standard drawdown methodology,
- treatment of non-trading days.

Only populate unresolved when information is missing or ambiguous in a way
that prevents the system from knowing what analysis the user wants.

Examples:

"Analyze the correlation between LVMH and Hermes over 2 years"
-> unresolved = []

"Compare LVMH and Hermes over 2 years"
-> unresolved should indicate that the metric to compare is missing.

"Compare their performance and risk since 2021"
-> performance is explicit, but risk is ambiguous between supported
risk metrics such as volatility and drawdown.
Record that ambiguity in unresolved.
Do not silently map risk to volatility.

Entity extraction rules:

- Preserve asset and universe references as closely as possible to the
  wording used by the user.
- Do not embellish, expand or rewrite a named universe.
- For example, if the user says "CAC 40", return "CAC 40", not
  "CAC 40 constituents", "CAC 40 stocks" or another reformulation.
- Entity canonicalization belongs to the downstream resolver, not to
  the understanding layer.

""".strip()

    @staticmethod
    def _build_refinement_instructions(
        today: date,
    ) -> str:
        return f"""
    You are the clarification layer of an equity quantitative
    analysis system.

    Today is {today.isoformat()}.

    You receive:
    1. a previous structured AnalysisRequest,
    2. a new user clarification.

    Your task is to return the updated AnalysisRequest.

    Rules:

    1. Preserve all valid information from the previous request unless
    the clarification explicitly changes it.

    2. Use the clarification only to resolve, complete or modify the
    previous request.

    3. Do not treat the clarification as a completely new standalone
    question unless it clearly replaces the previous request.

    4. Remove an item from unresolved once the clarification resolves it.

    5. Keep unresolved items that remain ambiguous or unanswered.

    6. If the clarification introduces another supported metric, add it
    to the existing metrics rather than discarding previously requested
    metrics unless the user explicitly asks to replace them.

    7. Preserve assets, universe, dates, benchmark, constraints,
    ranking_direction, top_n, performance_measure and horizons unless the
    clarification explicitly changes them.

    8. Do not perform financial calculations.

    9. Do not answer the user.

    10. Do not invent missing information.

    11. Put only genuine additional analytical restrictions that are not already
    represented by another request field in constraints. Never encode metric or
    ordinary price wording such as "maximum drawdown", "historical volatility",
    "performance", "closing price", or "close price" as constraints.

    12. Preserve explicit assets and an explicit universe independently. If the
    clarification names both, populate both fields.

    13. Set ranking_direction only when the user explicitly requests an ordering
    direction. A generic rank request leaves it null; do not infer "highest" from
    objective = rank alone.

    14. Preserve the distinction between total, annualized, relative, and excess
    return performance. A benchmark alone does not change total or annualized
    performance into relative performance. Set relative or excess_return only
    when the user explicitly asks for that calculation. Standard horizons are
    1m, 3m, 6m, ytd, 1y, and 3y. Horizon requests use start_date = null and
    end_date as their anchor.

    Supported objectives:
    - get
    - compare
    - rank
    - analyze

    Supported metrics:
    - price
    - performance
    - volatility
    - correlation
    - drawdown

    Example:

    Previous request:
    objective = compare
    metrics = [performance]
    assets = [Schneider Electric, Safran]
    unresolved = [
    "risk is ambiguous between volatility and drawdown"
    ]

    Clarification:
    "Volatility"

    Updated request:
    objective = compare
    metrics = [performance, volatility]
    assets = [Schneider Electric, Safran]
    unresolved = []

    The previous structured request is authoritative context.
    The clarification should refine it, not rebuild the analysis from
    scratch.
    """.strip()
