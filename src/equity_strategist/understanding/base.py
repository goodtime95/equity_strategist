from typing import Protocol

from equity_strategist.domain.analysis_request import AnalysisRequest


class UnderstandingProvider(Protocol):
    """Convert natural-language questions into structured analysis requests."""

    def understand(
        self,
        question: str,
    ) -> AnalysisRequest: ...

    def refine(
        self,
        previous_request: AnalysisRequest,
        clarification: str,
    ) -> AnalysisRequest: ...
