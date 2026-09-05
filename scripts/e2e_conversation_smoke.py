from equity_strategist.app import build_llm_equity_strategist
from equity_strategist.domain.analysis_plan import Capability
from equity_strategist.domain.analysis_request import AnalysisMetric
from equity_strategist.domain.request_validation import RequestStatus
from equity_strategist.strategists.graph import EquityStrategistGraph


def main() -> None:
    strategist = build_llm_equity_strategist()
    graph = EquityStrategistGraph(
        strategist=strategist,
    )

    thread_id = "conversation-smoke-1"

    print("=" * 100)
    print("TURN 1")
    print("=" * 100)

    first = graph.invoke(
        (
            "Compare Schneider Electric et Safran "
            "en performance et risque sur les deux dernières années."
        ),
        thread_id=thread_id,
    )

    print()
    print("Request:")
    print(first["request"])

    print()
    print("Validation:")
    print(first["validation"])

    print()
    print("Answer:")
    print(first["answer"])

    assert first["validation"].status == RequestStatus.NEEDS_CLARIFICATION
    assert "plan" not in first
    assert "execution" not in first

    print()
    print("=" * 100)
    print("TURN 2")
    print("=" * 100)

    second = graph.invoke(
        "Volatilité.",
        thread_id=thread_id,
    )

    print()
    print("Request:")
    print(second["request"])

    print()
    print("Validation:")
    print(second["validation"])

    print()
    print("Plan:")
    if "plan" in second:
        for step in second["plan"].steps:
            print(f"- {step.capability.value}")

    print()
    print("Answer:")
    print(second["answer"])

    assert second["validation"].status == RequestStatus.READY

    assert tuple(second["request"].metrics) == (
        AnalysisMetric.PERFORMANCE,
        AnalysisMetric.VOLATILITY,
    )

    actual_capabilities = tuple(step.capability for step in second["plan"].steps)

    assert actual_capabilities == (
        Capability.COMPARE_PERFORMANCE,
        Capability.COMPARE_VOLATILITY,
    )

    assert second["execution"] is not None

    print()
    print("=" * 100)
    print("CONVERSATION SMOKE TEST PASSED")
    print("=" * 100)


if __name__ == "__main__":
    main()
