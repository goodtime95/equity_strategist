import json

from openai import OpenAI

from equity_strategist.domain.analysis_execution import (
    AnalysisExecutionResult,
)
from equity_strategist.domain.request_validation import (
    RequestValidationResult,
)
from equity_strategist.interpretation.deterministic import (
    DeterministicInterpretation,
)
from equity_strategist.interpretation.evidence import (
    serialize_execution_evidence,
)


class LLMInterpretation:
    """Explain deterministic execution evidence without calculating new facts."""

    def __init__(
        self,
        client: OpenAI | None = None,
        model: str = "gpt-5.6",
        fallback: DeterministicInterpretation | None = None,
    ) -> None:
        self.client = client or OpenAI()
        self.model = model
        self.fallback = fallback or DeterministicInterpretation()

    def interpret(
        self,
        execution: AnalysisExecutionResult,
    ) -> str:
        evidence = serialize_execution_evidence(execution)

        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=self._instructions(),
                input=json.dumps(evidence, ensure_ascii=False),
            )
            answer = response.output_text.strip()
        except Exception:
            return self.fallback.interpret(execution)

        if not answer:
            return self.fallback.interpret(execution)

        return answer

    def interpret_validation(
        self,
        validation: RequestValidationResult,
    ) -> str:
        return self.fallback.interpret_validation(validation)

    @staticmethod
    def _instructions() -> str:
        return """
You are the final interpretation layer of an equity analysis system.

The input is JSON evidence produced by deterministic financial services.
Use only this evidence. Summarize, compare, and explain the supplied facts in
clear language.

Rules:
- Do not calculate, derive, estimate, normalize, round, or convert any value.
- When citing dates, symbols, names, metrics, ranks, or values, reproduce the
  supplied representation exactly.
- Do not introduce numbers or facts absent from the evidence.
- Do not add causal explanations, forecasts, recommendations, or external
  market context.
- Do not claim that a relationship is causal.
- State limitations visible in the evidence, such as use of a previous trading
  session.
- Return only the user-facing interpretation.
""".strip()
