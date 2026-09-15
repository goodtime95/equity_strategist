import json
import traceback
from dataclasses import dataclass
from enum import StrEnum

from openai import OpenAI

from equity_strategist.app import build_llm_equity_strategist
from equity_strategist.domain.analysis_plan import Capability
from equity_strategist.domain.analysis_request import (
    AnalysisHorizon,
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
    PerformanceMeasure,
    RankingDirection,
)
from equity_strategist.domain.request_validation import RequestStatus
from equity_strategist.interpretation.evidence import serialize_execution_evidence
from equity_strategist.strategists.graph import EquityStrategistGraph


class PipelineLayer(StrEnum):
    UNDERSTANDING = "understanding"
    VALIDATION = "validation"
    PLANNING = "planning"
    EXECUTION = "execution/data"
    INTERPRETATION = "interpretation"


@dataclass(frozen=True, slots=True)
class ExpectedBehavior:
    objective: AnalysisObjective
    metrics: tuple[AnalysisMetric, ...]
    assets: tuple[str, ...]
    status: RequestStatus
    universe: str | None = None
    ranking_direction: RankingDirection | None = None
    top_n: int | None = None
    benchmark: str | None = None
    requires_constraints: bool = False
    capabilities: tuple[Capability, ...] = ()
    issue_contains: tuple[str, ...] = ()
    performance_measure: PerformanceMeasure = PerformanceMeasure.TOTAL
    horizons: tuple[AnalysisHorizon, ...] = ()


@dataclass(frozen=True, slots=True)
class E2ECase:
    name: str
    question: str
    expected: ExpectedBehavior
    clarification: str | None = None
    initial_expected: ExpectedBehavior | None = None


@dataclass(frozen=True, slots=True)
class Failure:
    layer: PipelineLayer
    message: str


@dataclass(frozen=True, slots=True)
class CaseResult:
    name: str
    failures: tuple[Failure, ...]

    @property
    def passed(self) -> bool:
        return not self.failures


@dataclass(frozen=True, slots=True)
class LLMCallRecord:
    layer: PipelineLayer
    succeeded: bool
    output_text: str | None = None
    error: str | None = None


class RecordingResponses:
    """Record live LLM stages while delegating every call to OpenAI."""

    def __init__(self, delegate: object) -> None:
        self.delegate = delegate
        self.records: list[LLMCallRecord] = []

    def create(self, **kwargs: object) -> object:
        layer = (
            PipelineLayer.UNDERSTANDING
            if "text" in kwargs
            else PipelineLayer.INTERPRETATION
        )

        try:
            response = self.delegate.create(**kwargs)
        except Exception as exc:
            self.records.append(
                LLMCallRecord(
                    layer=layer,
                    succeeded=False,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            raise

        output_text = getattr(response, "output_text", None)
        self.records.append(
            LLMCallRecord(
                layer=layer,
                succeeded=isinstance(output_text, str) and bool(output_text.strip()),
                output_text=output_text if isinstance(output_text, str) else None,
            )
        )
        return response


class RecordingOpenAI:
    def __init__(self, delegate: OpenAI) -> None:
        self.responses = RecordingResponses(delegate.responses)


CASES = (
    E2ECase(
        name="performance_comparison_external_assets",
        question=(
            "Compare the historical performance of Schneider Electric and Safran "
            "from 2024-01-01 to 2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.COMPARE,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=("Schneider Electric", "Safran"),
            status=RequestStatus.READY,
            capabilities=(Capability.COMPARE_PERFORMANCE,),
        ),
    ),
    E2ECase(
        name="volatility_comparison_external_assets",
        question=(
            "Compare the historical volatility of Siemens and SAP from "
            "2024-01-01 to 2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.COMPARE,
            metrics=(AnalysisMetric.VOLATILITY,),
            assets=("Siemens", "SAP"),
            status=RequestStatus.READY,
            capabilities=(Capability.COMPARE_VOLATILITY,),
        ),
    ),
    E2ECase(
        name="performance_and_volatility",
        question=(
            "Compare Schneider Electric, Safran and TotalEnergies by historical "
            "performance and volatility from 2024-01-01 to 2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.COMPARE,
            metrics=(AnalysisMetric.PERFORMANCE, AnalysisMetric.VOLATILITY),
            assets=("Schneider Electric", "Safran", "TotalEnergies"),
            status=RequestStatus.READY,
            capabilities=(
                Capability.COMPARE_PERFORMANCE,
                Capability.COMPARE_VOLATILITY,
            ),
        ),
    ),
    E2ECase(
        name="correlation",
        question=(
            "Analyze the historical correlation between SAP and Siemens from "
            "2024-01-01 to 2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.ANALYZE,
            metrics=(AnalysisMetric.CORRELATION,),
            assets=("SAP", "Siemens"),
            status=RequestStatus.READY,
            capabilities=(Capability.ANALYZE_CORRELATION,),
        ),
    ),
    E2ECase(
        name="drawdown",
        question=(
            "Compare the maximum drawdown of Safran and TotalEnergies from "
            "2024-01-01 to 2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.COMPARE,
            metrics=(AnalysisMetric.DRAWDOWN,),
            assets=("Safran", "TotalEnergies"),
            status=RequestStatus.READY,
            capabilities=(Capability.COMPARE_DRAWDOWN,),
        ),
    ),
    E2ECase(
        name="price_on_non_trading_date",
        question="What was Schneider Electric's closing price on 2023-12-24?",
        expected=ExpectedBehavior(
            objective=AnalysisObjective.GET,
            metrics=(AnalysisMetric.PRICE,),
            assets=("Schneider Electric",),
            status=RequestStatus.READY,
            capabilities=(Capability.PRICE_ON_DATE,),
        ),
    ),
    E2ECase(
        name="explicit_asset_performance_ranking",
        question=(
            "Rank Schneider Electric, Safran and Siemens from highest to lowest "
            "historical performance between 2024-01-01 and 2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.RANK,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=("Schneider Electric", "Safran", "Siemens"),
            status=RequestStatus.READY,
            ranking_direction=RankingDirection.HIGHEST,
            capabilities=(Capability.RANK_PERFORMANCE,),
        ),
    ),
    E2ECase(
        name="explicit_asset_volatility_ranking",
        question=(
            "Rank LVMH, SAP and Siemens from highest to lowest historical "
            "volatility between 2024-01-01 and 2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.RANK,
            metrics=(AnalysisMetric.VOLATILITY,),
            assets=("LVMH", "SAP", "Siemens"),
            status=RequestStatus.READY,
            ranking_direction=RankingDirection.HIGHEST,
            capabilities=(Capability.RANK_VOLATILITY,),
        ),
    ),
    E2ECase(
        name="top_n_performance_ranking",
        question=(
            "Show the top 2 of LVMH, SAP and Siemens by historical performance "
            "between 2024-01-01 and 2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.RANK,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=("LVMH", "SAP", "Siemens"),
            status=RequestStatus.READY,
            ranking_direction=RankingDirection.HIGHEST,
            top_n=2,
            capabilities=(Capability.RANK_PERFORMANCE,),
        ),
    ),
    E2ECase(
        name="bottom_n_volatility_ranking",
        question=(
            "Show the bottom 2, meaning the least volatile, of LVMH, SAP and "
            "Siemens by historical volatility between 2024-01-01 and 2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.RANK,
            metrics=(AnalysisMetric.VOLATILITY,),
            assets=("LVMH", "SAP", "Siemens"),
            status=RequestStatus.READY,
            ranking_direction=RankingDirection.LOWEST,
            top_n=2,
            capabilities=(Capability.RANK_VOLATILITY,),
        ),
    ),
    E2ECase(
        name="universe_performance_ranking",
        question=(
            "Rank the CAC 40 universe from highest to lowest historical performance "
            "between 2025-01-01 and 2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.RANK,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=(),
            status=RequestStatus.READY,
            universe="CAC 40",
            ranking_direction=RankingDirection.HIGHEST,
            capabilities=(Capability.RANK_PERFORMANCE,),
        ),
    ),
    E2ECase(
        name="ytd_performance",
        question=(
            "Compare Schneider Electric and Safran by YTD performance as of 2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.COMPARE,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=("Schneider Electric", "Safran"),
            status=RequestStatus.READY,
            horizons=(AnalysisHorizon.YEAR_TO_DATE,),
            capabilities=(Capability.COMPARE_PERFORMANCE,),
        ),
    ),
    E2ECase(
        name="standard_performance_horizons",
        question=(
            "Compare Schneider Electric and Safran's total performance over 1M, "
            "3M, 6M, 1Y and 3Y as of 2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.COMPARE,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=("Schneider Electric", "Safran"),
            status=RequestStatus.READY,
            horizons=(
                AnalysisHorizon.ONE_MONTH,
                AnalysisHorizon.THREE_MONTHS,
                AnalysisHorizon.SIX_MONTHS,
                AnalysisHorizon.ONE_YEAR,
                AnalysisHorizon.THREE_YEARS,
            ),
            capabilities=(Capability.COMPARE_PERFORMANCE,),
        ),
    ),
    E2ECase(
        name="annualized_performance",
        question=(
            "Compare the annualized performance of Siemens and SAP over 3Y as "
            "of 2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.COMPARE,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=("Siemens", "SAP"),
            status=RequestStatus.READY,
            performance_measure=PerformanceMeasure.ANNUALIZED,
            horizons=(AnalysisHorizon.THREE_YEARS,),
            capabilities=(Capability.COMPARE_PERFORMANCE,),
        ),
    ),
    E2ECase(
        name="top_n_selected_horizon",
        question=(
            "Show the top 2 of LVMH, SAP and Siemens by 6M performance as of "
            "2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.RANK,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=("LVMH", "SAP", "Siemens"),
            status=RequestStatus.READY,
            ranking_direction=RankingDirection.HIGHEST,
            top_n=2,
            horizons=(AnalysisHorizon.SIX_MONTHS,),
            capabilities=(Capability.RANK_PERFORMANCE,),
        ),
    ),
    E2ECase(
        name="bottom_n_selected_horizon",
        question=(
            "Show the bottom 2 of LVMH, SAP and Siemens by 1Y performance as of "
            "2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.RANK,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=("LVMH", "SAP", "Siemens"),
            status=RequestStatus.READY,
            ranking_direction=RankingDirection.LOWEST,
            top_n=2,
            horizons=(AnalysisHorizon.ONE_YEAR,),
            capabilities=(Capability.RANK_PERFORMANCE,),
        ),
    ),
    E2ECase(
        name="relative_performance",
        question=(
            "Compare Schneider Electric and Safran's relative performance versus "
            "the S&P 500 over 1Y as of 2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.COMPARE,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=("Schneider Electric", "Safran"),
            status=RequestStatus.READY,
            benchmark="S&P 500",
            performance_measure=PerformanceMeasure.RELATIVE,
            horizons=(AnalysisHorizon.ONE_YEAR,),
            capabilities=(Capability.COMPARE_PERFORMANCE,),
        ),
    ),
    E2ECase(
        name="excess_return",
        question=(
            "Compare Schneider Electric and Safran's excess return over the "
            "S&P 500 over 1Y as of 2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.COMPARE,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=("Schneider Electric", "Safran"),
            status=RequestStatus.READY,
            benchmark="S&P 500",
            performance_measure=PerformanceMeasure.EXCESS_RETURN,
            horizons=(AnalysisHorizon.ONE_YEAR,),
            capabilities=(Capability.COMPARE_PERFORMANCE,),
        ),
    ),
    E2ECase(
        name="ambiguous_risk",
        question=(
            "Compare Schneider Electric and Safran by performance and risk from "
            "2024-01-01 to 2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.COMPARE,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=("Schneider Electric", "Safran"),
            status=RequestStatus.NEEDS_CLARIFICATION,
        ),
    ),
    E2ECase(
        name="missing_metric",
        question=(
            "Compare Schneider Electric and Safran from 2024-01-01 to 2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.COMPARE,
            metrics=(),
            assets=("Schneider Electric", "Safran"),
            status=RequestStatus.NEEDS_CLARIFICATION,
            issue_contains=("metric",),
        ),
    ),
    E2ECase(
        name="missing_assets",
        question="Compare historical performance from 2024-01-01 to 2025-12-31.",
        expected=ExpectedBehavior(
            objective=AnalysisObjective.COMPARE,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=(),
            status=RequestStatus.NEEDS_CLARIFICATION,
            issue_contains=("asset",),
        ),
    ),
    E2ECase(
        name="unsupported_capability",
        question=(
            "Rank LVMH, SAP and Siemens by highest maximum drawdown between "
            "2024-01-01 and 2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.RANK,
            metrics=(AnalysisMetric.DRAWDOWN,),
            assets=("LVMH", "SAP", "Siemens"),
            status=RequestStatus.UNSUPPORTED,
            ranking_direction=RankingDirection.HIGHEST,
            issue_contains=("unsupported analysis combination",),
        ),
    ),
    E2ECase(
        name="benchmark_performance",
        question=(
            "Compare Schneider Electric and Safran by historical performance "
            "against the S&P 500 benchmark from 2024-01-01 to 2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.COMPARE,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=("Schneider Electric", "Safran"),
            status=RequestStatus.READY,
            benchmark="S&P 500",
            capabilities=(Capability.COMPARE_PERFORMANCE,),
        ),
    ),
    E2ECase(
        name="unsupported_free_form_constraint",
        question=(
            "Compare Schneider Electric and Safran by historical performance from "
            "2024-01-01 to 2025-12-31, restricted to EUR-denominated listings."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.COMPARE,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=("Schneider Electric", "Safran"),
            status=RequestStatus.UNSUPPORTED,
            requires_constraints=True,
            issue_contains=("constraints",),
        ),
    ),
    E2ECase(
        name="assets_and_universe_ambiguity",
        question=(
            "Within the CAC 40 universe, rank only LVMH, TotalEnergies and Safran "
            "by historical performance from 2024-01-01 to 2025-12-31."
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.RANK,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=("LVMH", "TotalEnergies", "Safran"),
            status=RequestStatus.NEEDS_CLARIFICATION,
            universe="CAC 40",
            issue_contains=("one asset source",),
        ),
    ),
    E2ECase(
        name="multi_turn_risk_clarification",
        question=(
            "Compare Schneider Electric and Safran by performance and risk from "
            "2024-01-01 to 2025-12-31."
        ),
        clarification="Use historical volatility for risk.",
        initial_expected=ExpectedBehavior(
            objective=AnalysisObjective.COMPARE,
            metrics=(AnalysisMetric.PERFORMANCE,),
            assets=("Schneider Electric", "Safran"),
            status=RequestStatus.NEEDS_CLARIFICATION,
        ),
        expected=ExpectedBehavior(
            objective=AnalysisObjective.COMPARE,
            metrics=(AnalysisMetric.PERFORMANCE, AnalysisMetric.VOLATILITY),
            assets=("Schneider Electric", "Safran"),
            status=RequestStatus.READY,
            capabilities=(
                Capability.COMPARE_PERFORMANCE,
                Capability.COMPARE_VOLATILITY,
            ),
        ),
    ),
)


def _request_payload(request: AnalysisRequest) -> dict[str, object]:
    return {
        "objective": request.objective.value,
        "metrics": [metric.value for metric in request.metrics],
        "assets": list(request.assets),
        "universe": request.universe,
        "start_date": (
            request.start_date.isoformat() if request.start_date is not None else None
        ),
        "end_date": (
            request.end_date.isoformat() if request.end_date is not None else None
        ),
        "target_date": (
            request.target_date.isoformat() if request.target_date is not None else None
        ),
        "market_period": request.market_period,
        "benchmark": request.benchmark,
        "constraints": list(request.constraints),
        "ranking_direction": (
            request.ranking_direction.value
            if request.ranking_direction is not None
            else None
        ),
        "top_n": request.top_n,
        "performance_measure": request.performance_measure.value,
        "horizons": [horizon.value for horizon in request.horizons],
        "unresolved": list(request.unresolved),
    }


def _print_state(label: str, state: dict) -> None:
    print(f"\n{label}")
    print("-" * 100)

    request = state.get("request")
    print("AnalysisRequest:")
    print(
        json.dumps(
            _request_payload(request) if request is not None else None,
            ensure_ascii=False,
            indent=2,
        )
    )

    validation = state.get("validation")
    print("\nValidation:")
    if validation is None:
        print("null")
    else:
        print(
            json.dumps(
                {
                    "status": validation.status.value,
                    "issues": list(validation.issues),
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    plan = state.get("plan")
    print("\nPlan capabilities:")
    print(
        json.dumps(
            [step.capability.value for step in plan.steps] if plan is not None else [],
            indent=2,
        )
    )

    execution = state.get("execution")
    print("\nDeterministic execution result:")
    print(repr(execution))
    print("\nStructured evidence:")
    print(
        json.dumps(
            serialize_execution_evidence(execution) if execution is not None else None,
            ensure_ascii=False,
            indent=2,
        )
    )

    print("\nFinal answer:")
    print(state.get("answer"))


def _check_state(
    state: dict,
    expected: ExpectedBehavior,
    require_llm_interpretation: bool,
    llm_records: list[LLMCallRecord],
) -> list[Failure]:
    failures: list[Failure] = []
    request = state.get("request")

    if request is None:
        return [Failure(PipelineLayer.UNDERSTANDING, "no AnalysisRequest returned")]

    request_checks = (
        (request.objective == expected.objective, "objective", request.objective),
        (request.metrics == expected.metrics, "metrics", request.metrics),
        (request.assets == expected.assets, "assets", request.assets),
        (request.universe == expected.universe, "universe", request.universe),
        (
            request.ranking_direction == expected.ranking_direction,
            "ranking_direction",
            request.ranking_direction,
        ),
        (request.top_n == expected.top_n, "top_n", request.top_n),
        (request.benchmark == expected.benchmark, "benchmark", request.benchmark),
        (
            request.performance_measure == expected.performance_measure,
            "performance_measure",
            request.performance_measure,
        ),
        (request.horizons == expected.horizons, "horizons", request.horizons),
    )

    for matches, field, actual in request_checks:
        if not matches:
            failures.append(
                Failure(
                    PipelineLayer.UNDERSTANDING,
                    f"unexpected {field}: {actual!r}",
                )
            )

    if expected.requires_constraints and not request.constraints:
        failures.append(
            Failure(
                PipelineLayer.UNDERSTANDING,
                "expected at least one parsed constraint",
            )
        )
    elif not expected.requires_constraints and request.constraints:
        failures.append(
            Failure(
                PipelineLayer.UNDERSTANDING,
                f"unexpected constraints: {request.constraints!r}",
            )
        )

    validation = state.get("validation")
    if validation is None:
        failures.append(Failure(PipelineLayer.VALIDATION, "no validation returned"))
        return failures

    if validation.status != expected.status:
        failures.append(
            Failure(
                PipelineLayer.VALIDATION,
                f"expected {expected.status.value}, got {validation.status.value}",
            )
        )

    issues_text = " ".join(validation.issues).casefold()
    for fragment in expected.issue_contains:
        if fragment.casefold() not in issues_text:
            failures.append(
                Failure(
                    PipelineLayer.VALIDATION,
                    f"validation issues do not contain {fragment!r}",
                )
            )

    plan = state.get("plan")
    execution = state.get("execution")
    answer = state.get("answer")

    if expected.status != RequestStatus.READY:
        if plan is not None:
            failures.append(
                Failure(PipelineLayer.PLANNING, "non-ready request produced a plan")
            )
        if execution is not None:
            failures.append(
                Failure(
                    PipelineLayer.EXECUTION,
                    "non-ready request produced an execution result",
                )
            )
        if not isinstance(answer, str) or not answer.strip():
            failures.append(
                Failure(
                    PipelineLayer.VALIDATION,
                    "non-ready request produced no validation answer",
                )
            )
        return failures

    if plan is None:
        failures.append(Failure(PipelineLayer.PLANNING, "ready request has no plan"))
    else:
        capabilities = tuple(step.capability for step in plan.steps)
        if capabilities != expected.capabilities:
            failures.append(
                Failure(
                    PipelineLayer.PLANNING,
                    "expected capabilities "
                    f"{tuple(item.value for item in expected.capabilities)!r}, got "
                    f"{tuple(item.value for item in capabilities)!r}",
                )
            )

    if execution is None:
        failures.append(
            Failure(PipelineLayer.EXECUTION, "ready request has no execution result")
        )
    else:
        evidence = serialize_execution_evidence(execution)
        evidence_steps = evidence.get("steps")
        if not isinstance(evidence_steps, list) or not evidence_steps:
            failures.append(
                Failure(PipelineLayer.EXECUTION, "execution produced no evidence")
            )

    if not isinstance(answer, str) or not answer.strip():
        failures.append(
            Failure(PipelineLayer.INTERPRETATION, "ready request has no final answer")
        )

    if require_llm_interpretation:
        interpretation_records = [
            record
            for record in llm_records
            if record.layer == PipelineLayer.INTERPRETATION
        ]
        if not interpretation_records:
            failures.append(
                Failure(
                    PipelineLayer.INTERPRETATION,
                    "no live LLM interpretation call was recorded",
                )
            )
        elif not interpretation_records[-1].succeeded:
            failures.append(
                Failure(
                    PipelineLayer.INTERPRETATION,
                    "LLM interpretation failed or returned an empty response; "
                    "deterministic fallback was used",
                )
            )

    return failures


def _exception_layer(trace: str) -> PipelineLayer:
    if "understanding/llm.py" in trace or "openai" in trace.casefold():
        return PipelineLayer.UNDERSTANDING
    if "validator.py" in trace:
        return PipelineLayer.VALIDATION
    if "planner.py" in trace:
        return PipelineLayer.PLANNING
    if "interpretation/" in trace:
        return PipelineLayer.INTERPRETATION
    return PipelineLayer.EXECUTION


def run_case(
    graph: EquityStrategistGraph,
    recording_client: RecordingOpenAI,
    case: E2ECase,
) -> CaseResult:
    print("\n" + "=" * 100)
    print(f"CASE: {case.name}")
    print("=" * 100)
    print("Question:")
    print(case.question)

    recording_client.responses.records.clear()
    thread_id = f"product-battery-{case.name}"

    try:
        first_state = graph.invoke(case.question, thread_id=thread_id)
        _print_state("TURN 1", first_state)

        if case.clarification is None:
            failures = _check_state(
                state=first_state,
                expected=case.expected,
                require_llm_interpretation=case.expected.status == RequestStatus.READY,
                llm_records=recording_client.responses.records,
            )
        else:
            if case.initial_expected is None:
                raise AssertionError("multi-turn case requires initial_expected")

            failures = _check_state(
                state=first_state,
                expected=case.initial_expected,
                require_llm_interpretation=False,
                llm_records=recording_client.responses.records,
            )

            print("\nClarification:")
            print(case.clarification)
            second_state = graph.invoke(case.clarification, thread_id=thread_id)
            _print_state("TURN 2", second_state)
            failures.extend(
                _check_state(
                    state=second_state,
                    expected=case.expected,
                    require_llm_interpretation=True,
                    llm_records=recording_client.responses.records,
                )
            )

    except Exception:
        trace = traceback.format_exc()
        print("\nPIPELINE EXCEPTION:")
        print(trace)
        failures = [
            Failure(
                layer=_exception_layer(trace),
                message=trace.strip().splitlines()[-1],
            )
        ]

    print("\nResult:")
    if failures:
        for failure in failures:
            print(f"FAIL [{failure.layer.value}] {failure.message}")
    else:
        print("PASS")

    return CaseResult(name=case.name, failures=tuple(failures))


def _print_summary(results: list[CaseResult]) -> None:
    print("\n\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        layers = ", ".join(sorted({failure.layer.value for failure in result.failures}))
        print(f"{status:<4} | {result.name:<45} | {layers or 'complete'}")

    passed = sum(result.passed for result in results)
    print(f"\n{passed}/{len(results)} cases passed")

    failures_by_layer = {layer: [] for layer in PipelineLayer}
    for result in results:
        for failure in result.failures:
            failures_by_layer[failure.layer].append(f"{result.name}: {failure.message}")

    print("\nFailures by pipeline layer:")
    for layer, failures in failures_by_layer.items():
        print(f"\n{layer.value}: {len(failures)}")
        for failure in failures:
            print(f"- {failure}")


def main() -> None:
    recording_client = RecordingOpenAI(OpenAI())
    strategist = build_llm_equity_strategist(client=recording_client)
    graph = EquityStrategistGraph(strategist=strategist)

    results = [
        run_case(
            graph=graph,
            recording_client=recording_client,
            case=case,
        )
        for case in CASES
    ]
    _print_summary(results)

    if any(not result.passed for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
