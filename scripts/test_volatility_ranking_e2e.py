from equity_strategist.app import build_equity_strategist


def main() -> None:
    strategist = build_equity_strategist()

    question = "Classe LVMH, Hermès et ASML par volatilité sur les 2 dernières années"

    print("Question:")
    print(question)
    print()

    request = strategist.understanding.understand(question)

    print("Understanding:")
    print(f"Objective: {request.objective.value}")
    print(
        "Metrics:",
        [metric.value for metric in request.metrics],
    )
    print(f"Assets: {request.assets}")
    print(f"Period: {request.start_date} -> {request.end_date}")
    print()

    print("Answer:")
    print(strategist.answer(question))


if __name__ == "__main__":
    main()
