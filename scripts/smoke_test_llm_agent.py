from equity_strategist.app import (
    build_llm_equity_strategist,
)


def main() -> None:
    strategist = build_llm_equity_strategist()

    question = (
        "Entre LVMH, Hermès et ASML, compare leur "
        "performance et leur volatilité sur les "
        "deux dernières années."
    )

    print("=" * 80)
    print("LLM EQUITY STRATEGIST — END-TO-END SMOKE TEST")
    print()
    print("Question:")
    print(question)
    print()

    request = strategist.understand(question)

    print("Understanding:")
    print(request)
    print()

    validation = strategist.validator.validate(request)

    print("Validation:")
    print(validation)
    print()

    if not validation.is_ready:
        print("Stopped before execution.")
        return

    plan = strategist.planner.plan(request)

    print("Plan:")
    for step in plan.steps:
        print(f"- {step.capability.value}")
    print()

    execution = strategist.executor.execute(plan)

    print("Answer:")
    print(strategist.interpret(execution))
    print()

    print("=" * 80)


if __name__ == "__main__":
    main()
