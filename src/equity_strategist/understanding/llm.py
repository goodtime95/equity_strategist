import json
from datetime import date

from openai import OpenAI

from equity_strategist.domain.analysis_request import (
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
)

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
            "items": {
                "type": "string",
            },
        },
        "universe": {
            "type": ["string", "null"],
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
            "items": {
                "type": "string",
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
            user_context=question,
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

7. If the request refers to an investment universe rather than
   explicit assets, populate universe and leave assets empty.

8. If information is ambiguous or missing, record a concise
   description in unresolved.

9. Do not invent an asset, date, benchmark or universe.

10. "risk" alone should not automatically be interpreted as
    volatility unless the question clearly implies historical
    volatility.

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
