from typing import TypedDict

from equity_strategist.domain.analysis_execution import (
    AnalysisExecutionResult,
)
from equity_strategist.domain.analysis_plan import AnalysisPlan
from equity_strategist.domain.analysis_request import AnalysisRequest
from equity_strategist.domain.request_validation import (
    RequestValidationResult,
)


class EquityGraphState(TypedDict, total=False):
    question: str
    request: AnalysisRequest
    validation: RequestValidationResult
    plan: AnalysisPlan
    execution: AnalysisExecutionResult
    answer: str
