from equity_strategist.app import build_equity_strategist


def main():

    strategist = build_equity_strategist()

    answer = strategist.answer(
        "Compare la volatilité de LVMH et Hermès sur les 2 dernières années"
    )

    print(answer)


if __name__ == "__main__":
    main()
