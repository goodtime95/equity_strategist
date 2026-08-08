from equity_strategist.app import build_equity_strategist


def main() -> None:
    strategist = build_equity_strategist()

    question = "Compare la volatilité de LVMH et Hermès sur les 2 dernières années"

    print("=" * 60)
    print("QUESTION")
    print("=" * 60)
    print(question)
    print()

    request = strategist.understand(question)

    print("=" * 60)
    print("UNDERSTAND")
    print("=" * 60)
    print(f"Objective : {request.objective}")
    print(f"Metrics   : {[metric.value for metric in request.metrics]}")
    print(f"Assets    : {list(request.assets)}")
    print(f"Start     : {request.start_date}")
    print(f"End       : {request.end_date}")
    print()

    plan = strategist.planner.plan(request)

    print("=" * 60)
    print("PLAN")
    print("=" * 60)

    for index, step in enumerate(
        plan.steps,
        start=1,
    ):
        print(f"{index}. {step.capability.value}")

    print()

    execution = strategist.executor.execute(plan)

    print("=" * 60)
    print("EXECUTE")
    print("=" * 60)

    for index, step_result in enumerate(
        execution.step_results,
        start=1,
    ):
        print(
            f"{index}. {step_result.capability.value} -> "
            f"{type(step_result.result).__name__}"
        )

    print()

    answer = strategist.interpret(execution)

    print("=" * 60)
    print("ANSWER")
    print("=" * 60)
    print(answer)


if __name__ == "__main__":
    main()
