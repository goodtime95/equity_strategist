import json

import pytest

from equity_strategist.domain.analysis_request import (
    AnalysisMetric,
    AnalysisObjective,
    RankingDirection,
)
from equity_strategist.domain.request_validation import RequestStatus
from equity_strategist.strategists.validator import AnalysisRequestValidator
from equity_strategist.understanding.llm import (
    LLMUnderstanding,
)


class FakeResponse:
    output_text = """
    {
        "objective": "compare",
        "metrics": [
            "performance",
            "volatility"
        ],
        "assets": [
            "LVMH",
            "Hermès",
            "ASML"
        ],
        "universe": null,
        "start_date": "2024-08-15",
        "end_date": "2026-08-15",
        "target_date": null,
        "benchmark": null,
        "constraints": [],
        "ranking_direction": null,
        "top_n": null,
        "unresolved": []
    }
    """


class FakeResponses:
    def create(self, **kwargs):
        return FakeResponse()


class FakeOpenAI:
    def __init__(self) -> None:
        self.responses = FakeResponses()


def test_llm_understanding_builds_analysis_request() -> None:
    understanding = LLMUnderstanding(
        client=FakeOpenAI(),
    )

    request = understanding.understand(
        "Compare LVMH, Hermès et ASML "
        "en performance et volatilité "
        "sur les deux dernières années"
    )

    assert request.objective == AnalysisObjective.COMPARE

    assert request.metrics == (
        AnalysisMetric.PERFORMANCE,
        AnalysisMetric.VOLATILITY,
    )

    assert request.assets == (
        "LVMH",
        "Hermès",
        "ASML",
    )

    assert request.start_date.isoformat() == "2024-08-15"
    assert request.end_date.isoformat() == "2026-08-15"


class FakeRankingResponse:
    output_text = """
    {
        "objective": "rank",
        "metrics": ["volatility"],
        "assets": ["LVMH", "Hermès", "ASML"],
        "universe": null,
        "start_date": "2025-01-01",
        "end_date": "2026-01-01",
        "target_date": null,
        "benchmark": null,
        "constraints": [],
        "ranking_direction": "lowest",
        "top_n": 2,
        "unresolved": []
    }
    """


class FakeRankingResponses:
    def create(self, **kwargs):
        return FakeRankingResponse()


class FakeRankingOpenAI:
    def __init__(self) -> None:
        self.responses = FakeRankingResponses()


def test_llm_understanding_extracts_ranking_controls() -> None:
    request = LLMUnderstanding(client=FakeRankingOpenAI()).understand(
        "Show the two least volatile stocks"
    )

    assert request.ranking_direction == RankingDirection.LOWEST
    assert request.top_n == 2


class PayloadResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.output_text = json.dumps(payload)


class CapturingResponses:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> PayloadResponse:
        self.calls.append(kwargs)
        return PayloadResponse(self.payload)


class CapturingOpenAI:
    def __init__(self, payload: dict[str, object]) -> None:
        self.responses = CapturingResponses(payload)


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "objective": "compare",
        "metrics": ["performance"],
        "assets": ["Schneider Electric", "Safran"],
        "universe": None,
        "start_date": "2024-01-01",
        "end_date": "2025-12-31",
        "target_date": None,
        "benchmark": None,
        "constraints": [],
        "ranking_direction": None,
        "top_n": None,
        "unresolved": [],
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    (
        "question",
        "payload",
        "expected_objective",
        "expected_metric",
        "expected_status",
    ),
    [
        (
            "Compare the maximum drawdown of Safran and TotalEnergies from "
            "2024-01-01 to 2025-12-31.",
            _payload(
                metrics=["drawdown"],
                assets=["Safran", "TotalEnergies"],
            ),
            AnalysisObjective.COMPARE,
            AnalysisMetric.DRAWDOWN,
            RequestStatus.READY,
        ),
        (
            "What was Schneider Electric's closing price on 2023-12-24?",
            _payload(
                objective="get",
                metrics=["price"],
                assets=["Schneider Electric"],
                start_date=None,
                end_date=None,
                target_date="2023-12-24",
            ),
            AnalysisObjective.GET,
            AnalysisMetric.PRICE,
            RequestStatus.READY,
        ),
        (
            "Rank LVMH, SAP and Siemens by highest maximum drawdown between "
            "2024-01-01 and 2025-12-31.",
            _payload(
                objective="rank",
                metrics=["drawdown"],
                assets=["LVMH", "SAP", "Siemens"],
                ranking_direction="highest",
            ),
            AnalysisObjective.RANK,
            AnalysisMetric.DRAWDOWN,
            RequestStatus.UNSUPPORTED,
        ),
        (
            "Within the CAC 40 universe, rank only LVMH, TotalEnergies and Safran "
            "by historical performance from 2024-01-01 to 2025-12-31.",
            _payload(
                objective="rank",
                assets=["LVMH", "TotalEnergies", "Safran"],
                universe="CAC 40",
            ),
            AnalysisObjective.RANK,
            AnalysisMetric.PERFORMANCE,
            RequestStatus.NEEDS_CLARIFICATION,
        ),
    ],
)
def test_llm_understanding_preserves_typed_fields_without_false_constraints(
    question: str,
    payload: dict[str, object],
    expected_objective: AnalysisObjective,
    expected_metric: AnalysisMetric,
    expected_status: RequestStatus,
) -> None:
    client = CapturingOpenAI(payload)

    request = LLMUnderstanding(client=client).understand(question)

    assert request.objective == expected_objective
    assert request.metrics == (expected_metric,)
    assert request.constraints == ()
    assert AnalysisRequestValidator().validate(request).status == expected_status

    instructions = client.responses.calls[0]["instructions"]
    assert "only genuine additional analytical restrictions" in instructions
    assert "If the user names both, populate both assets and universe" in instructions


def test_llm_understanding_preserves_genuine_unsupported_constraint() -> None:
    client = CapturingOpenAI(_payload(constraints=["EUR-denominated listings only"]))

    request = LLMUnderstanding(client=client).understand(
        "Compare Schneider Electric and Safran by performance from 2024-01-01 "
        "to 2025-12-31, restricted to EUR-denominated listings."
    )

    assert request.constraints == ("EUR-denominated listings only",)
    assert (
        AnalysisRequestValidator().validate(request).status == RequestStatus.UNSUPPORTED
    )
