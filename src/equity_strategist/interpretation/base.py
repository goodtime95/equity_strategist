from typing import Protocol

from equity_strategist.domain.analysis_execution import (
    AnalysisExecutionResult,
)
from equity_strategist.domain.request_validation import (
    RequestValidationResult,
)
from equity_strategist.interpretation.context import InterpretationContext


class InterpretationProvider(Protocol):
    """Convert structured deterministic results into readable answers."""

    def interpret(
        self,
        execution: AnalysisExecutionResult,
        context: InterpretationContext | None = None,
    ) -> str: ...

    def interpret_validation(
        self,
        validation: RequestValidationResult,
        context: InterpretationContext | None = None,
    ) -> str: ...
