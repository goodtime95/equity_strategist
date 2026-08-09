from equity_strategist.app import build_equity_strategist


def main() -> None:
    strategist = build_equity_strategist()

    question = (
        "Compare le drawdown de LVMH, Hermès "
        "et ASML sur les 2 dernières années"
    )

    print(strategist.answer(question))


if __name__ == "__main__":
    main()
