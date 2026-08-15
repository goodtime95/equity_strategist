from dataclasses import dataclass
from datetime import date

from equity_strategist.domain.analysis_request import (
    AnalysisMetric,
    AnalysisObjective,
)
from equity_strategist.understanding.llm import LLMUnderstanding


@dataclass(frozen=True)
class ExpectedRequest:
    objective: AnalysisObjective
    metrics: tuple[AnalysisMetric, ...]
    assets: tuple[str, ...] = ()
    universe: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    target_date: date | None = None
    expect_unresolved: bool = False


@dataclass(frozen=True)
class TestCase:
    name: str
    question: str
    expected: ExpectedRequest


TODAY = date(2026, 8, 15)


CASES = (
    TestCase(
        name="performance_rank_5y",
        question=(
            "Entre LVMH et Hermès, lequel a le mieux "
            "performé sur les 5 dernières années ?"
        ),
        expected=ExpectedRequest(
            objective=AnalysisObjective.RANK,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=("LVMH", "Hermès"),
            start_date=date(2021, 8, 15),
            end_date=TODAY,
        ),
    ),
    TestCase(
        name="three_metric_compare",
        question=(
            "Compare ASML, Nvidia et LVMH en performance, "
            "volatilité et drawdown depuis 2023."
        ),
        expected=ExpectedRequest(
            objective=AnalysisObjective.COMPARE,
            metrics=(
                AnalysisMetric.PERFORMANCE,
                AnalysisMetric.VOLATILITY,
                AnalysisMetric.DRAWDOWN,
            ),
            assets=("ASML", "Nvidia", "LVMH"),
            start_date=date(2023, 1, 1),
            end_date=TODAY,
        ),
    ),
    TestCase(
        name="correlation_analysis",
        question=(
            "Analyse la corrélation entre LVMH, Hermès "
            "et ASML sur les 3 dernières années."
        ),
        expected=ExpectedRequest(
            objective=AnalysisObjective.ANALYZE,
            metrics=(AnalysisMetric.CORRELATION,),
            assets=("LVMH", "Hermès", "ASML"),
            start_date=date(2023, 8, 15),
            end_date=TODAY,
        ),
    ),
    TestCase(
        name="volatility_rank",
        question=("Classe Nvidia, ASML et LVMH du plus au moins volatile depuis 2022."),
        expected=ExpectedRequest(
            objective=AnalysisObjective.RANK,
            metrics=(AnalysisMetric.VOLATILITY,),
            assets=("Nvidia", "ASML", "LVMH"),
            start_date=date(2022, 1, 1),
            end_date=TODAY,
        ),
    ),
    TestCase(
        name="price_on_date",
        question=("Quel était le prix d’ASML le 24 décembre 2023 ?"),
        expected=ExpectedRequest(
            objective=AnalysisObjective.GET,
            metrics=(AnalysisMetric.PRICE,),
            assets=("ASML",),
            target_date=date(2023, 12, 24),
        ),
    ),
    TestCase(
        name="drawdown_rank",
        question=(
            "Parmi LVMH, Hermès et ASML, qui a le mieux "
            "résisté en drawdown sur les deux dernières années ?"
        ),
        expected=ExpectedRequest(
            objective=AnalysisObjective.RANK,
            metrics=(AnalysisMetric.DRAWDOWN,),
            assets=("LVMH", "Hermès", "ASML"),
            start_date=date(2024, 8, 15),
            end_date=TODAY,
        ),
    ),
    TestCase(
        name="performance_compare_since_jan_2024",
        question=(
            "Je veux comparer les performances de LVMH et Hermès depuis janvier 2024."
        ),
        expected=ExpectedRequest(
            objective=AnalysisObjective.COMPARE,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=("LVMH", "Hermès"),
            start_date=date(2024, 1, 1),
            end_date=TODAY,
        ),
    ),
    TestCase(
        name="ambiguous_risk",
        question=(
            "Comment se comparent LVMH et Hermès "
            "en termes de performance et de risque depuis 2021 ?"
        ),
        expected=ExpectedRequest(
            objective=AnalysisObjective.COMPARE,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=("LVMH", "Hermès"),
            start_date=date(2021, 1, 1),
            end_date=TODAY,
            expect_unresolved=True,
        ),
    ),
    TestCase(
        name="missing_metric",
        question=(
            "Compare Schneider Electric et Safran sur les deux dernières années."
        ),
        expected=ExpectedRequest(
            objective=AnalysisObjective.COMPARE,
            metrics=(),
            assets=(
                "Schneider Electric",
                "Safran",
            ),
            start_date=date(2024, 8, 15),
            end_date=TODAY,
            expect_unresolved=True,
        ),
    ),
    TestCase(
        name="cac40_universe_rank",
        question=(
            "Parmi les valeurs du CAC 40, classe les meilleures "
            "performances depuis début 2025."
        ),
        expected=ExpectedRequest(
            objective=AnalysisObjective.RANK,
            metrics=(AnalysisMetric.PERFORMANCE,),
            universe="CAC 40",
            start_date=date(2025, 1, 1),
            end_date=TODAY,
        ),
    ),
)


def normalize_text(value: str) -> str:
    return value.casefold().strip()


def assert_request(
    actual,
    expected: ExpectedRequest,
) -> list[str]:
    errors: list[str] = []

    if actual.objective != expected.objective:
        errors.append(
            f"objective: expected {expected.objective.value}, "
            f"got {actual.objective.value}"
        )

    if actual.metrics != expected.metrics:
        errors.append(
            "metrics: expected "
            f"{tuple(metric.value for metric in expected.metrics)}, "
            "got "
            f"{tuple(metric.value for metric in actual.metrics)}"
        )

    if actual.assets != expected.assets:
        errors.append(f"assets: expected {expected.assets}, got {actual.assets}")

    if actual.universe != expected.universe:
        errors.append(f"universe: expected {expected.universe}, got {actual.universe}")

    if actual.start_date != expected.start_date:
        errors.append(
            f"start_date: expected {expected.start_date}, got {actual.start_date}"
        )

    if actual.end_date != expected.end_date:
        errors.append(f"end_date: expected {expected.end_date}, got {actual.end_date}")

    if actual.target_date != expected.target_date:
        errors.append(
            f"target_date: expected {expected.target_date}, got {actual.target_date}"
        )

    if expected.expect_unresolved and not actual.unresolved:
        errors.append("expected unresolved information, but unresolved is empty")

    if not expected.expect_unresolved and actual.unresolved:
        errors.append(f"expected no unresolved information, got {actual.unresolved}")

    return errors


def main() -> None:
    understanding = LLMUnderstanding()

    passed = 0
    failed = 0

    for index, case in enumerate(
        CASES,
        start=1,
    ):
        print("=" * 80)
        print(f"{index}. {case.name}")
        print(case.question)
        print()

        request = understanding.understand(case.question)

        print("Actual:")
        print(request)
        print()

        errors = assert_request(
            actual=request,
            expected=case.expected,
        )

        if errors:
            failed += 1

            print("❌ FAIL")

            for error in errors:
                print(f"  - {error}")
        else:
            passed += 1
            print("✅ PASS")

        print()

    print("=" * 80)
    print(f"RESULT: {passed} passed, {failed} failed, {len(CASES)} total")


if __name__ == "__main__":
    main()
