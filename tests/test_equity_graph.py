from datetime import date

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
    PerformanceComparisonResult,
    PerformanceItem,
)
from equity_strategist.domain.request_validation import (
    RequestStatus,
    RequestValidationResult,
)
from equity_strategist.strategists.graph import EquityStrategistGraph


class FakeUnderstanding:
    def understand(
        self,
        question: str,
    ) -> AnalysisRequest:
        return AnalysisRequest(
            objective=AnalysisObjective.COMPARE,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=("LVMH", "Hermès"),
            start_date=date(2024, 1, 1),
            end_date=date(2025, 1, 1),
            user_context=question,
        )


class FakeValidator:
    def validate(
        self,
        request: AnalysisRequest,
    ) -> RequestValidationResult:
        return RequestValidationResult(
            status=RequestStatus.READY,
            issues=(),
        )


class FakePlanner:
    def plan(
        self,
        request: AnalysisRequest,
    ) -> AnalysisPlan:
        return AnalysisPlan(
            request=request,
            steps=(
                PlanStep(
                    capability=Capability.COMPARE_PERFORMANCE,
                ),
            ),
        )


class FakeExecutor:
    def execute(
        self,
        plan: AnalysisPlan,
    ) -> AnalysisExecutionResult:
        result = PerformanceComparisonResult(
            start_date=date(2024, 1, 1),
            end_date=date(2025, 1, 1),
            items=(
                PerformanceItem(
                    symbol="MC.PA",
                    name="LVMH",
                    performance=0.10,
                ),
                PerformanceItem(
                    symbol="RMS.PA",
                    name="Hermès",
                    performance=0.05,
                ),
            ),
        )

        return AnalysisExecutionResult(
            plan=plan,
            step_results=(
                StepExecutionResult(
                    capability=Capability.COMPARE_PERFORMANCE,
                    result=result,
                ),
            ),
        )


class FakeStrategist:
    def __init__(self) -> None:
        self.understanding = FakeUnderstanding()
        self.validator = FakeValidator()
        self.planner = FakePlanner()
        self.executor = FakeExecutor()

    def understand(
        self,
        question: str,
    ) -> AnalysisRequest:
        return self.understanding.understand(question)

    def interpret(
        self,
        execution: AnalysisExecutionResult,
    ) -> str:
        return "fake answer"

    @staticmethod
    def _interpret_validation(
        validation: RequestValidationResult,
    ) -> str:
        return "validation stopped"


def test_graph_returns_answer_for_supported_request() -> None:
    graph = EquityStrategistGraph(
        strategist=FakeStrategist(),
    )

    result = graph.invoke(
        "Compare LVMH et Hermès."
    )

    assert result["validation"].is_ready
    assert result["plan"] is not None
    assert result["execution"] is not None
    assert result["answer"] == "fake answer"

class FakeClarificationValidator:
    def validate(
        self,
        request: AnalysisRequest,
    ) -> RequestValidationResult:
        return RequestValidationResult(
            status=RequestStatus.NEEDS_CLARIFICATION,
            issues=("metric clarification required",),
        )


class FakeClarificationStrategist(FakeStrategist):
    def __init__(self) -> None:
        super().__init__()
        self.validator = FakeClarificationValidator()


def test_graph_stops_when_clarification_is_needed() -> None:
    graph = EquityStrategistGraph(
        strategist=FakeClarificationStrategist(),
    )

    result = graph.invoke(
        "Compare LVMH et Hermès."
    )

    assert not result["validation"].is_ready
    assert "plan" not in result
    assert "execution" not in result
    assert result["answer"] == "validation stopped"