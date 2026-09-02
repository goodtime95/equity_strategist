from typing import Literal

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

        return builder.compile()

    def invoke(
        self,
        question: str,
    ) -> EquityGraphState:
        return self.graph.invoke(
            {
                "question": question,
            }
        )

    def _understand(
        self,
        state: EquityGraphState,
    ) -> dict:
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
