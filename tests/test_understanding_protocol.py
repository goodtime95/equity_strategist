from equity_strategist.domain.analysis_request import (
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
)
from equity_strategist.understanding.base import (
    UnderstandingProvider,
)


class FakeUnderstanding:
    def understand(
        self,
        question: str,
    ) -> AnalysisRequest:
        return AnalysisRequest(
            objective=AnalysisObjective.COMPARE,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=("LVMH", "Hermès"),
        )


def test_understanding_provider_supports_structural_typing() -> None:
    provider: UnderstandingProvider = FakeUnderstanding()

    request = provider.understand("Compare LVMH et Hermès")

    assert request.objective == AnalysisObjective.COMPARE
    assert request.metrics == (AnalysisMetric.PERFORMANCE,)
