from equity_strategist.domain.analysis_request import (
    AnalysisMetric,
    AnalysisObjective,
)
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
