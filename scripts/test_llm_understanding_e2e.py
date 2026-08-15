from equity_strategist.understanding.llm import (
    LLMUnderstanding,
)


def main() -> None:
    understanding = LLMUnderstanding()

    questions = [
        (
            "Entre LVMH, Hermès et ASML, "
            "compare leur performance et leur volatilité "
            "sur les deux dernières années"
        ),
        ("Qui de Nvidia, ASML et LVMH a le mieux performé depuis 2024 ?"),
        ("Quel était le prix de LVMH le 15 mars 2020 ?"),
    ]

    for question in questions:
        print("=" * 80)
        print(question)
        print()

        request = understanding.understand(question)

        print(request)
        print()


if __name__ == "__main__":
    main()
