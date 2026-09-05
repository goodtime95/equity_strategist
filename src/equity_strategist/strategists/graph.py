from typing import Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from equity_strategist.domain.request_validation import (
    RequestStatus,
)
from equity_strategist.strategists.equity_strategist import (
    EquityStrategist,
)
from equity_strategist.strategists.graph_state import (
    EquityGraphResult,
    EquityGraphState,
    analysis_request_from_state,
    analysis_request_to_state,
    validation_from_state,
    validation_to_state,
)


class EquityStrategistGraph:
    """LangGraph orchestration for the equity strategist workflow."""

    def __init__(
        self,
        strategist: EquityStrategist,
    ) -> None:
        self.strategist = strategist
        self.checkpointer = InMemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(EquityGraphState)

        builder.add_node(
            "understand",
            self._understand,
        )
        builder.add_node(
            "validate",
            self._validate,
        )
        builder.add_node(
            "plan",
            self._plan,
        )
        builder.add_node(
            "execute",
            self._execute,
        )
        builder.add_node(
            "interpret",
            self._interpret,
        )
        builder.add_node(
            "interpret_validation",
            self._interpret_validation,
        )

        builder.add_edge(
            START,
            "understand",
        )
        builder.add_edge(
            "understand",
            "validate",
        )

        builder.add_conditional_edges(
            "validate",
            self._route_after_validation,
            {
                "ready": "plan",
                "stop": "interpret_validation",
            },
        )

        builder.add_edge(
            "plan",
            "execute",
        )
        builder.add_edge(
            "execute",
            "interpret",
        )
        builder.add_edge(
            "interpret",
            END,
        )
        builder.add_edge(
            "interpret_validation",
            END,
        )

        return builder.compile(checkpointer=self.checkpointer)

    def invoke(
        self,
        question: str,
        thread_id: str = "default",
    ) -> EquityGraphResult:
        state = self.graph.invoke(
            {
                "question": question,
            },
            config={
                "configurable": {
                    "thread_id": thread_id,
                }
            },
        )

        result: EquityGraphResult = {
            "question": state["question"],
        }

        if "request" in state:
            result["request"] = analysis_request_from_state(state["request"])

        if "validation" in state:
            result["validation"] = validation_from_state(state["validation"])

        if "plan" in state:
            result["plan"] = state["plan"]

        if "execution" in state:
            result["execution"] = state["execution"]

        if "answer" in state:
            result["answer"] = state["answer"]

        return result

    def _understand(
        self,
        state: EquityGraphState,
    ) -> dict:
        previous_request_data = state.get("request")
        previous_validation_data = state.get("validation")

        if (
            previous_request_data is not None
            and previous_validation_data is not None
            and previous_validation_data["status"]
            == RequestStatus.NEEDS_CLARIFICATION.value
        ):
            previous_request = analysis_request_from_state(previous_request_data)

            request = self.strategist.refine(
                previous_request=previous_request,
                clarification=state["question"],
            )

        else:
            request = self.strategist.understand(state["question"])

        return {
            "request": analysis_request_to_state(request),
        }

    def _validate(
        self,
        state: EquityGraphState,
    ) -> dict:
        request = analysis_request_from_state(state["request"])

        validation = self.strategist.validator.validate(request)

        return {
            "validation": validation_to_state(validation),
        }

    @staticmethod
    def _route_after_validation(
        state: EquityGraphState,
    ) -> Literal["ready", "stop"]:
        if state["validation"]["status"] == RequestStatus.READY.value:
            return "ready"

        return "stop"

    def _plan(
        self,
        state: EquityGraphState,
    ) -> dict:
        request = analysis_request_from_state(state["request"])

        plan = self.strategist.planner.plan(request)

        return {
            "plan": plan,
        }

    def _execute(
        self,
        state: EquityGraphState,
    ) -> dict:
        execution = self.strategist.executor.execute(state["plan"])

        return {
            "execution": execution,
        }

    def _interpret(
        self,
        state: EquityGraphState,
    ) -> dict:
        answer = self.strategist.interpret(state["execution"])

        return {
            "answer": answer,
        }

    def _interpret_validation(
        self,
        state: EquityGraphState,
    ) -> dict:
        validation = validation_from_state(state["validation"])

        answer = self.strategist._interpret_validation(validation)

        return {
            "answer": answer,
        }
