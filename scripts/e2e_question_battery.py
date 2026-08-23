from dataclasses import dataclass

from equity_strategist.app import (
    build_llm_equity_strategist,
)
from equity_strategist.domain.analysis_plan import Capability
from equity_strategist.domain.request_validation import (
    RequestStatus,
)


@dataclass(frozen=True, slots=True)
class E2ECase:
    name: str
    question: str
    expected_status: RequestStatus
    expected_capabilities: tuple[Capability, ...] = ()


CASES = (
    E2ECase(
        name="external_fr_performance",
        question=(
            "Compare Schneider Electric et Safran "
            "en performance sur les deux dernières années."
        ),
        expected_status=RequestStatus.READY,
        expected_capabilities=(Capability.COMPARE_PERFORMANCE,),
    ),
    E2ECase(
        name="external_de_volatility",
        question=("Compare Siemens et SAP en volatilité sur les 18 derniers mois."),
        expected_status=RequestStatus.READY,
        expected_capabilities=(Capability.COMPARE_VOLATILITY,),
    ),
    E2ECase(
        name="primary_listing_totalenergies",
        question=(
            "Compare TotalEnergies et Safran en performance depuis janvier 2025."
        ),
        expected_status=RequestStatus.READY,
        expected_capabilities=(Capability.COMPARE_PERFORMANCE,),
    ),
    E2ECase(
        name="multi_metric_external_assets",
        question=(
            "Compare Schneider Electric, Safran et Siemens "
            "en performance et volatilité sur deux ans."
        ),
        expected_status=RequestStatus.READY,
        expected_capabilities=(
            Capability.COMPARE_PERFORMANCE,
            Capability.COMPARE_VOLATILITY,
        ),
    ),
    E2ECase(
        name="correlation_external_assets",
        question=(
            "Analyse la corrélation entre Schneider Electric "
            "et Siemens sur les trois dernières années."
        ),
        expected_status=RequestStatus.READY,
        expected_capabilities=(Capability.ANALYZE_CORRELATION,),
    ),
    E2ECase(
        name="drawdown_external_assets",
        question=(
            "Compare les drawdowns de Safran, Siemens "
            "et TotalEnergies depuis début 2024."
        ),
        expected_status=RequestStatus.READY,
        expected_capabilities=(Capability.COMPARE_DRAWDOWN,),
    ),
    E2ECase(
        name="performance_ranking",
        question=(
            "Classe Schneider Electric, Safran et Siemens "
            "du meilleur au moins bon en performance "
            "sur les deux dernières années."
        ),
        expected_status=RequestStatus.READY,
        expected_capabilities=(Capability.RANK_PERFORMANCE,),
    ),
    E2ECase(
        name="volatility_ranking",
        question=(
            "Classe Schneider Electric, Safran et Siemens "
            "par volatilité sur les deux dernières années."
        ),
        expected_status=RequestStatus.READY,
        expected_capabilities=(Capability.RANK_VOLATILITY,),
    ),
    E2ECase(
        name="price_on_date",
        question=("Quel était le cours de Schneider Electric le 24 décembre 2023 ?"),
        expected_status=RequestStatus.READY,
        expected_capabilities=(Capability.PRICE_ON_DATE,),
    ),
    E2ECase(
        name="ambiguous_risk",
        question=(
            "Compare Schneider Electric et Safran "
            "en performance et risque sur deux ans."
        ),
        expected_status=RequestStatus.NEEDS_CLARIFICATION,
    ),
    E2ECase(
        name="missing_assets",
        question=("Compare la performance sur les deux dernières années."),
        expected_status=RequestStatus.NEEDS_CLARIFICATION,
    ),
    E2ECase(
        name="unsupported_rank_drawdown",
        question=(
            "Classe Schneider Electric, Safran et Siemens "
            "selon leur drawdown sur les deux dernières années."
        ),
        expected_status=RequestStatus.UNSUPPORTED,
    ),
    E2ECase(
        name="cac40_performance_ranking",
        question=(
            "Classe les actions du CAC 40 par performance sur les douze derniers mois."
        ),
        expected_status=RequestStatus.READY,
        expected_capabilities=(Capability.RANK_PERFORMANCE,),
    ),
    E2ECase(
        name="unsupported_universe_volatility",
        question=(
            "Classe les actions du CAC 40 par volatilité sur les douze derniers mois."
        ),
        expected_status=RequestStatus.UNSUPPORTED,
    ),
)


def run_case(
    strategist,
    case: E2ECase,
) -> tuple[bool, str]:
    print()
    print("=" * 100)
    print(f"CASE: {case.name}")
    print("=" * 100)
    print()
    print("Question:")
    print(case.question)
    print()

    try:
        request = strategist.understand(case.question)
    except Exception as exc:
        print("UNDERSTANDING ERROR:")
        print(f"{type(exc).__name__}: {exc}")
        return False, "understanding"

    print("Understanding:")
    print(request)
    print()

    try:
        validation = strategist.validator.validate(request)
    except Exception as exc:
        print("VALIDATION ERROR:")
        print(f"{type(exc).__name__}: {exc}")
        return False, "validation"

    print("Validation:")
    print(validation)
    print()

    if validation.status != case.expected_status:
        print(
            "EXPECTATION FAILURE: "
            f"expected status={case.expected_status.value}, "
            f"got={validation.status.value}"
        )
        return False, "status"

    if not validation.is_ready:
        answer = strategist.answer_request(request)

        print("Answer:")
        print(answer)

        return True, "validation_stop"

    try:
        plan = strategist.planner.plan(request)
    except Exception as exc:
        print("PLANNING ERROR:")
        print(f"{type(exc).__name__}: {exc}")
        return False, "planning"

    actual_capabilities = tuple(step.capability for step in plan.steps)

    print("Plan:")
    for capability in actual_capabilities:
        print(f"- {capability.value}")
    print()

    if case.expected_capabilities and actual_capabilities != case.expected_capabilities:
        print(
            "EXPECTATION FAILURE: "
            f"expected capabilities="
            f"{tuple(c.value for c in case.expected_capabilities)}, "
            f"got="
            f"{tuple(c.value for c in actual_capabilities)}"
        )
        return False, "capabilities"

    try:
        execution = strategist.executor.execute(plan)
    except Exception as exc:
        print("EXECUTION ERROR:")
        print(f"{type(exc).__name__}: {exc}")
        return False, "execution"

    try:
        answer = strategist.interpret(execution)
    except Exception as exc:
        print("INTERPRETATION ERROR:")
        print(f"{type(exc).__name__}: {exc}")
        return False, "interpretation"

    print("Answer:")
    print(answer)

    return True, "success"


def main() -> None:
    strategist = build_llm_equity_strategist()

    results = []

    for case in CASES:
        passed, stage = run_case(
            strategist=strategist,
            case=case,
        )

        results.append(
            (
                case.name,
                passed,
                stage,
            )
        )

    print()
    print()
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print()

    passed_count = 0

    for name, passed, stage in results:
        status = "PASS" if passed else "FAIL"

        if passed:
            passed_count += 1

        print(f"{status:<4} | {name:<35} | {stage}")

    print()
    print(f"{passed_count}/{len(results)} cases passed")


if __name__ == "__main__":
    main()
