from datetime import date

from equity_strategist.app import build_equity_strategist
from equity_strategist.domain.analysis_request import (
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
)


def main() -> None:
    strategist = build_equity_strategist()

    request = AnalysisRequest(
        objective=AnalysisObjective.RANK,
        metrics=(AnalysisMetric.DRAWDOWN,),
        assets=(
            "LVMH",
            "Hermès",
            "ASML",
        ),
        start_date=date(2024, 1, 1),
        end_date=date(2026, 1, 1),
    )

    print("=" * 80)
    print("SMOKE TEST — unsupported request")
    print()
    print("Request:")
    print(request)
    print()

    answer = strategist.answer_request(request)

    print("Answer:")
    print(answer)
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
