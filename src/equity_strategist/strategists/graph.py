from typing import Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from equity_strategist.domain.request_validation import RequestStatus
from equity_strategist.strategists.equity_strategist import (
    EquityStrategist,
)
from equity_strategist.strategists.graph_state import (
    EquityGraphState,
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
    ) -> EquityGraphState:
        return self.graph.invoke(
            {
                "question": question,
            },
            config={
                "configurable": {
                    "thread_id": thread_id,
                }
            },
        )

    def _understand(
        self,
        state: EquityGraphState,
    ) -> dict:
        previous_request = state.get("request")
        previous_validation = state.get("validation")

        if (
            previous_request is not None
            and previous_validation is not None
            and previous_validation.status == RequestStatus.NEEDS_CLARIFICATION
        ):
            request = self.strategist.refine(
                previous_request=previous_request,
                clarification=state["question"],
            )
        else:
            request = self.strategist.understand(state["question"])

        return {
            "request": request,
        }

    def _validate(
        self,
        state: EquityGraphState,
    ) -> dict:
        validation = self.strategist.validator.validate(state["request"])

        return {
            "validation": validation,
        }

    @staticmethod
    def _route_after_validation(
        state: EquityGraphState,
    ) -> Literal["ready", "stop"]:
        validation = state["validation"]

        if validation.status == RequestStatus.READY:
            return "ready"

        return "stop"

    def _plan(
        self,
        state: EquityGraphState,
    ) -> dict:
        plan = self.strategist.planner.plan(state["request"])

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
        answer = self.strategist._interpret_validation(state["validation"])

        return {
            "answer": answer,
        }
