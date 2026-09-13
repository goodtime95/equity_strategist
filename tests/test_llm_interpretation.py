import json
from datetime import date
from decimal import Decimal

import pytest

from equity_strategist.app import (
    build_equity_strategist,
    build_llm_equity_strategist,
)
from equity_strategist.domain.analysis_execution import (
    AnalysisExecutionResult,
    StepExecutionResult,
)
from equity_strategist.domain.analysis_plan import (
    AnalysisPlan,
    Capability,
    PlanStep,
)
from equity_strategist.domain.analysis_request import (
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
)
from equity_strategist.domain.analysis_results import (
    CorrelationAnalysisResult,
    CorrelationItem,
    DrawdownComparisonResult,
    DrawdownItem,
    PerformanceComparisonResult,
    PerformanceItem,
    RankingItem,
    RankingResult,
    VolatilityComparisonResult,
    VolatilityItem,
)
from equity_strategist.domain.asset import Asset
from equity_strategist.domain.request_validation import (
    RequestStatus,
    RequestValidationResult,
)
from equity_strategist.domain.results import PriceOnDateResult
from equity_strategist.interpretation.deterministic import (
    DeterministicInterpretation,
)
from equity_strategist.interpretation.evidence import (
    serialize_execution_evidence,
)
from equity_strategist.interpretation.llm import LLMInterpretation
from equity_strategist.understanding.llm import LLMUnderstanding


class FakeResponse:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text


class FakeResponses:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> FakeResponse:
        self.calls.append(kwargs)
        return FakeResponse(self.output_text)


class FakeOpenAI:
    def __init__(self, output_text: str = "Evidence-based answer") -> None:
        self.responses = FakeResponses(output_text)


class FailingResponses:
    def create(self, **kwargs: object) -> FakeResponse:
        raise RuntimeError("LLM unavailable")


class FailingOpenAI:
    responses = FailingResponses()


class MalformedResponse:
    def __init__(self, output_text: object) -> None:
        self.output_text = output_text


class MalformedResponses:
    def __init__(self, response: object) -> None:
        self.response = response

    def create(self, **kwargs: object) -> object:
        return self.response


class MalformedOpenAI:
    def __init__(self, response: object) -> None:
        self.responses = MalformedResponses(response)


def _execution(
    *step_results: StepExecutionResult,
) -> AnalysisExecutionResult:
    request = AnalysisRequest(
        objective=AnalysisObjective.RANK,
        metrics=(AnalysisMetric.PERFORMANCE,),
        assets=("LVMH", "Hermès"),
        start_date=date(2024, 1, 1),
        end_date=date(2025, 1, 1),
    )
    plan = AnalysisPlan(
        request=request,
        steps=tuple(PlanStep(capability=step.capability) for step in step_results),
    )
    return AnalysisExecutionResult(plan=plan, step_results=step_results)


def test_serialize_execution_evidence_preserves_deterministic_facts() -> None:
    ranking = RankingResult(
        metric="performance",
        start_date=date(2024, 1, 1),
        end_date=date(2025, 1, 1),
        items=(
            RankingItem(
                rank=1,
                symbol="MC.PA",
                name="LVMH",
                value=0.123456789,
            ),
        ),
    )
    price = PriceOnDateResult(
        asset=Asset(symbol="RMS.PA", name="Hermès", currency="EUR"),
        requested_date=date(2025, 1, 5),
        effective_date=date(2025, 1, 3),
        price=Decimal("2314.90"),
        price_type="close",
        used_previous_session=True,
    )

    evidence = serialize_execution_evidence(
        _execution(
            StepExecutionResult(Capability.RANK_PERFORMANCE, ranking),
            StepExecutionResult(Capability.PRICE_ON_DATE, price),
        )
    )

    assert evidence == {
        "steps": [
            {
                "capability": "rank_performance",
                "result": {
                    "type": "ranking",
                    "metric": "performance",
                    "start_date": "2024-01-01",
                    "end_date": "2025-01-01",
                    "items": [
                        {
                            "rank": 1,
                            "symbol": "MC.PA",
                            "name": "LVMH",
                            "value": "0.123456789",
                        }
                    ],
                },
            },
            {
                "capability": "price_on_date",
                "result": {
                    "type": "price_on_date",
                    "metric": "price",
                    "symbol": "RMS.PA",
                    "name": "Hermès",
                    "currency": "EUR",
                    "requested_date": "2025-01-05",
                    "effective_date": "2025-01-03",
                    "price": "2314.90",
                    "price_type": "close",
                    "used_previous_session": True,
                },
            },
        ]
    }


@pytest.mark.parametrize(
    ("capability", "result", "expected_result"),
    [
        (
            Capability.COMPARE_PERFORMANCE,
            PerformanceComparisonResult(
                date(2024, 1, 1),
                date(2025, 1, 1),
                (PerformanceItem("MC.PA", "LVMH", 0.2),),
            ),
            {
                "type": "performance_comparison",
                "metric": "performance",
                "start_date": "2024-01-01",
                "end_date": "2025-01-01",
                "items": [
                    {
                        "symbol": "MC.PA",
                        "name": "LVMH",
                        "value": "0.2",
                    }
                ],
            },
        ),
        (
            Capability.COMPARE_VOLATILITY,
            VolatilityComparisonResult(
                date(2024, 1, 1),
                date(2025, 1, 1),
                252,
                (VolatilityItem("MC.PA", "LVMH", 0.3),),
            ),
            {
                "type": "volatility_comparison",
                "metric": "volatility",
                "start_date": "2024-01-01",
                "end_date": "2025-01-01",
                "annualization_factor": 252,
                "items": [
                    {
                        "symbol": "MC.PA",
                        "name": "LVMH",
                        "value": "0.3",
                    }
                ],
            },
        ),
        (
            Capability.ANALYZE_CORRELATION,
            CorrelationAnalysisResult(
                date(2024, 1, 1),
                date(2025, 1, 1),
                (CorrelationItem("MC.PA", "LVMH", "RMS.PA", "Hermès", 0.7),),
            ),
            {
                "type": "correlation_analysis",
                "metric": "correlation",
                "start_date": "2024-01-01",
                "end_date": "2025-01-01",
                "items": [
                    {
                        "first_symbol": "MC.PA",
                        "first_name": "LVMH",
                        "second_symbol": "RMS.PA",
                        "second_name": "Hermès",
                        "value": "0.7",
                    }
                ],
            },
        ),
        (
            Capability.COMPARE_DRAWDOWN,
            DrawdownComparisonResult(
                date(2024, 1, 1),
                date(2025, 1, 1),
                (
                    DrawdownItem(
                        "MC.PA",
                        "LVMH",
                        -0.25,
                        date(2024, 2, 1),
                        date(2024, 3, 1),
                        date(2024, 6, 1),
                    ),
                ),
            ),
            {
                "type": "drawdown_comparison",
                "metric": "maximum_drawdown",
                "start_date": "2024-01-01",
                "end_date": "2025-01-01",
                "items": [
                    {
                        "symbol": "MC.PA",
                        "name": "LVMH",
                        "value": "-0.25",
                        "peak_date": "2024-02-01",
                        "trough_date": "2024-03-01",
                        "recovery_date": "2024-06-01",
                    }
                ],
            },
        ),
    ],
)
def test_serialize_execution_evidence_supports_comparison_results(
    capability: Capability,
    result: object,
    expected_result: dict[str, object],
) -> None:
    evidence = serialize_execution_evidence(
        _execution(StepExecutionResult(capability, result))
    )

    serialized_result = evidence["steps"][0]["result"]

    assert serialized_result == expected_result


def test_llm_interpretation_invokes_responses_with_only_evidence() -> None:
    client = FakeOpenAI("LVMH (MC.PA) ranks 1 with performance 0.123456789.")
    execution = _execution(
        StepExecutionResult(
            Capability.RANK_PERFORMANCE,
            RankingResult(
                metric="performance",
                start_date=date(2024, 1, 1),
                end_date=date(2025, 1, 1),
                items=(RankingItem(1, "MC.PA", "LVMH", 0.123456789),),
            ),
        )
    )

    answer = LLMInterpretation(client=client, model="test-model").interpret(execution)

    assert answer == "LVMH (MC.PA) ranks 1 with performance 0.123456789."
    assert len(client.responses.calls) == 1
    call = client.responses.calls[0]
    assert call["model"] == "test-model"
    assert json.loads(call["input"]) == serialize_execution_evidence(execution)
    assert "Do not calculate" in call["instructions"]
    assert "Do not add causal explanations" in call["instructions"]


def test_llm_interpretation_uses_deterministic_fallback_on_failure() -> None:
    execution = _execution(
        StepExecutionResult(
            Capability.COMPARE_PERFORMANCE,
            PerformanceComparisonResult(
                start_date=date(2024, 1, 1),
                end_date=date(2025, 1, 1),
                items=(PerformanceItem("MC.PA", "LVMH", 0.2),),
            ),
        )
    )

    answer = LLMInterpretation(client=FailingOpenAI()).interpret(execution)

    assert answer == DeterministicInterpretation().interpret(execution)


@pytest.mark.parametrize(
    "response",
    [
        object(),
        MalformedResponse(None),
        MalformedResponse(""),
        MalformedResponse("   "),
    ],
)
def test_llm_interpretation_falls_back_for_malformed_or_empty_response(
    response: object,
) -> None:
    execution = _execution(
        StepExecutionResult(
            Capability.COMPARE_PERFORMANCE,
            PerformanceComparisonResult(
                start_date=date(2024, 1, 1),
                end_date=date(2025, 1, 1),
                items=(PerformanceItem("MC.PA", "LVMH", 0.2),),
            ),
        )
    )

    answer = LLMInterpretation(client=MalformedOpenAI(response)).interpret(execution)

    assert answer == DeterministicInterpretation().interpret(execution)


def test_llm_interpretation_keeps_validation_deterministic() -> None:
    client = FakeOpenAI()
    validation = RequestValidationResult(
        status=RequestStatus.NEEDS_CLARIFICATION,
        issues=("at least one metric is required",),
    )

    answer = LLMInterpretation(client=client).interpret_validation(validation)

    assert answer == DeterministicInterpretation().interpret_validation(validation)
    assert client.responses.calls == []


def test_composition_roots_select_the_expected_interpretation() -> None:
    client = FakeOpenAI()

    deterministic = build_equity_strategist()
    llm = build_llm_equity_strategist(client=client)

    assert isinstance(deterministic.interpretation, DeterministicInterpretation)
    assert isinstance(llm.understanding, LLMUnderstanding)
    assert isinstance(llm.interpretation, LLMInterpretation)
    assert llm.understanding.client is client
    assert llm.interpretation.client is client
