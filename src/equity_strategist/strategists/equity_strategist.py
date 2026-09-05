from equity_strategist.domain.analysis_execution import (
    AnalysisExecutionResult,
)
from equity_strategist.domain.analysis_request import (
    AnalysisRequest,
)
from equity_strategist.domain.request_validation import (
    RequestValidationResult,
)
from equity_strategist.interpretation.base import InterpretationProvider
from equity_strategist.strategists.executor import EquityExecutor
from equity_strategist.strategists.planner import EquityPlanner
from equity_strategist.strategists.validator import (
    AnalysisRequestValidator,
)
from equity_strategist.understanding.base import (
    UnderstandingProvider,
)


class EquityStrategist:
    """Coordinate understanding, planning, execution and interpretation."""

    def __init__(
        self,
        understanding: UnderstandingProvider,
        planner: EquityPlanner,
        executor: EquityExecutor,
        validator: AnalysisRequestValidator,
        interpretation: InterpretationProvider,
    ) -> None:
        self.understanding = understanding
        self.planner = planner
        self.executor = executor
        self.validator = validator
        self.interpretation = interpretation

    def answer(
        self,
        question: str,
    ) -> str:
        """Answer a natural-language equity question."""
        request = self.understand(question)

        return self._answer_request(request)

    def answer_request(
        self,
        request: AnalysisRequest,
    ) -> str:
        """Execute a structured request and return a readable answer."""
        return self._answer_request(request)

    def _answer_request(
        self,
        request: AnalysisRequest,
    ) -> str:
        validation = self.validator.validate(request)

        if not validation.is_ready:
            return self._interpret_validation(validation)

        plan = self.planner.plan(request)
        execution = self.executor.execute(plan)

        return self.interpret(execution)

    def understand(
        self,
        question: str,
    ) -> AnalysisRequest:
        """Convert natural language into a structured request."""
        return self.understanding.understand(question)

    def refine(
        self,
        previous_request: AnalysisRequest,
        clarification: str,
    ) -> AnalysisRequest:
        """Refine a previous request using a user clarification."""
        return self.understanding.refine(
            previous_request=previous_request,
            clarification=clarification,
        )

    def interpret(
        self,
        execution: AnalysisExecutionResult,
    ) -> str:
        return self.interpretation.interpret(execution)

    def _interpret_validation(
        self,
        validation: RequestValidationResult,
    ) -> str:
        return self.interpretation.interpret_validation(validation)
