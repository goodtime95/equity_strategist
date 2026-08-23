from equity_strategist.app import (
    build_llm_equity_strategist,
)


def main() -> None:
    strategist = build_llm_equity_strategist()

    question = (
        "Compare Schneider Electric et Safran "
        "en performance sur les deux dernières années."
    )

    print("=" * 80)
    print("ASSET FALLBACK — END-TO-END SMOKE TEST")
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

    answer = strategist.answer_request(request)

    print("Answer:")
    print(answer)
    print()

    print("=" * 80)


if __name__ == "__main__":
    main()
