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

    def refine(
        self,
        previous_request: AnalysisRequest,
        clarification: str,
    ) -> AnalysisRequest:
        return AnalysisRequest(
            objective=previous_request.objective,
            metrics=(
                AnalysisMetric.PERFORMANCE,
                AnalysisMetric.VOLATILITY,
            ),
            assets=tuple(previous_request.assets),
            universe=previous_request.universe,
            start_date=previous_request.start_date,
            end_date=previous_request.end_date,
            target_date=previous_request.target_date,
            benchmark=previous_request.benchmark,
            constraints=tuple(previous_request.constraints),
            user_context=clarification,
            unresolved=(),
        )


class FakeClarificationUnderstanding:
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
            unresolved=("risk is ambiguous between volatility and drawdown",),
        )

    def refine(
        self,
        previous_request: AnalysisRequest,
        clarification: str,
    ) -> AnalysisRequest:
        assert clarification == "Volatility"

        return AnalysisRequest(
            objective=previous_request.objective,
            metrics=(
                AnalysisMetric.PERFORMANCE,
                AnalysisMetric.VOLATILITY,
            ),
            assets=tuple(previous_request.assets),
            universe=previous_request.universe,
            start_date=previous_request.start_date,
            end_date=previous_request.end_date,
            target_date=previous_request.target_date,
            benchmark=previous_request.benchmark,
            constraints=tuple(previous_request.constraints),
            user_context=clarification,
            unresolved=(),
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


class FakeConversationValidator:
    def validate(
        self,
        request: AnalysisRequest,
    ) -> RequestValidationResult:
        if request.unresolved:
            return RequestValidationResult(
                status=RequestStatus.NEEDS_CLARIFICATION,
                issues=tuple(request.unresolved),
            )

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

    def refine(
        self,
        previous_request: AnalysisRequest,
        clarification: str,
    ) -> AnalysisRequest:
        return self.understanding.refine(
            previous_request=previous_request,
            clarification=clarification,
        )

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


class FakeConversationStrategist(FakeStrategist):
    def __init__(self) -> None:
        super().__init__()

        self.understanding = FakeClarificationUnderstanding()
        self.validator = FakeConversationValidator()


def test_graph_returns_answer_for_supported_request() -> None:
    graph = EquityStrategistGraph(
        strategist=FakeStrategist(),
    )

    result = graph.invoke("Compare LVMH et Hermès.")

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

    result = graph.invoke("Compare LVMH et Hermès.")

    assert not result["validation"].is_ready
    assert "plan" not in result
    assert "execution" not in result
    assert result["answer"] == "validation stopped"

    def test_graph_persists_state_by_thread_id() -> None:
        graph = EquityStrategistGraph(
            strategist=FakeStrategist(),
        )

        first_result = graph.invoke(
            "Compare LVMH et Hermès.",
            thread_id="thread-1",
        )

        saved_state = graph.graph.get_state(
            {
                "configurable": {
                    "thread_id": "thread-1",
                }
            }
        )

        assert first_result["answer"] == "fake answer"

        assert saved_state.values["question"] == "Compare LVMH et Hermès."

        saved_request = saved_state.values["request"]
        first_request = first_result["request"]

        assert saved_request["objective"] == first_request.objective.value
        assert saved_request["metrics"] == [
            metric.value for metric in first_request.metrics
        ]
        assert saved_request["assets"] == list(first_request.assets)
        assert saved_request["start_date"] == (
            first_request.start_date.isoformat()
            if first_request.start_date is not None
            else None
        )
        assert saved_request["end_date"] == (
            first_request.end_date.isoformat()
            if first_request.end_date is not None
            else None
        )
        assert saved_request["universe"] == first_request.universe

        saved_validation = saved_state.values["validation"]
        first_validation = first_result["validation"]

        assert saved_validation["status"] == first_validation.status.value
        assert saved_validation["issues"] == list(first_validation.issues)

        assert "plan" not in saved_state.values
        assert "execution" not in saved_state.values


def test_graph_keeps_threads_isolated() -> None:
    graph = EquityStrategistGraph(
        strategist=FakeStrategist(),
    )

    graph.invoke(
        "First question",
        thread_id="thread-1",
    )

    graph.invoke(
        "Second question",
        thread_id="thread-2",
    )

    first_state = graph.graph.get_state(
        {
            "configurable": {
                "thread_id": "thread-1",
            }
        }
    )

    second_state = graph.graph.get_state(
        {
            "configurable": {
                "thread_id": "thread-2",
            }
        }
    )

    assert first_state.values["question"] == "First question"

    assert second_state.values["question"] == "Second question"


def test_graph_refines_request_across_two_turns() -> None:
    graph = EquityStrategistGraph(
        strategist=FakeConversationStrategist(),
    )

    first_result = graph.invoke(
        "Compare LVMH et Hermès en performance et risque.",
        thread_id="conversation-1",
    )

    assert first_result["validation"].status == RequestStatus.NEEDS_CLARIFICATION

    assert "plan" not in first_result
    assert "execution" not in first_result

    second_result = graph.invoke(
        "Volatility",
        thread_id="conversation-1",
    )

    assert second_result["validation"].status == RequestStatus.READY

    assert tuple(second_result["request"].metrics) == (
        AnalysisMetric.PERFORMANCE,
        AnalysisMetric.VOLATILITY,
    )

    assert tuple(second_result["request"].assets) == (
        "LVMH",
        "Hermès",
    )

    assert not second_result["request"].unresolved

    assert second_result["plan"] is not None
    assert second_result["execution"] is not None
    assert second_result["answer"] == "fake answer"
