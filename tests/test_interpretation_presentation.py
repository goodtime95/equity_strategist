"""Presentation context, additive contracts, and deterministic fallback coverage."""

import json
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from equity_strategist.domain.analysis_execution import StepExecutionResult
from equity_strategist.domain.analysis_plan import Capability
from equity_strategist.domain.analysis_request import PerformanceMeasure
from equity_strategist.domain.analysis_results import (
    CorrelationAnalysisResult,
    CorrelationItem,
    DrawdownComparisonResult,
    DrawdownItem,
    PerformanceAnalysisResult,
    PerformanceItem,
    PerformancePeriodResult,
    RankingItem,
    RankingResult,
    VolatilityComparisonResult,
    VolatilityItem,
)
from equity_strategist.interpretation.context import InterpretationContext
from equity_strategist.interpretation.deterministic import DeterministicInterpretation
from equity_strategist.interpretation.evidence import serialize_execution_evidence
from equity_strategist.interpretation.llm import LLMInterpretation
from equity_strategist.interpretation.presentation import display_value
from equity_strategist.strategists.graph import EquityStrategistGraph
from equity_strategist.strategists.graph_state import (
    analysis_request_to_state,
    validation_to_state,
)
from tests.test_llm_interpretation import FailingOpenAI, _execution
from tests.test_production_remediation import BASE_REQUEST, pipeline


@pytest.mark.parametrize(
    "value,metric,expected",
    [
        (2.8240268985197297, "performance", "282.40%"),
        (0.123456, "volatility", "12.35%"),
        (-0.045678, "maximum_drawdown", "-4.57%"),
        (0.123456, "correlation", "0.123"),
        (0.012345, "excess_return", "1.23 pp"),
        (Decimal("2314.901234"), "price", "2314.90"),
    ],
)
def test_metric_specific_display_rules(value, metric, expected):
    assert display_value(value, metric) == expected


@pytest.mark.parametrize(
    "question,language",
    [
        ("Quelle est la volatilité de Hermès ?", "fr"),
        ("What is the volatility of Hermès?", "en"),
        ("Compare Hermès and LVMH", "en"),
        ("Compare Hermès et LVMH", "fr"),
    ],
)
def test_language_detection_ignores_accents_in_asset_names(question, language):
    assert InterpretationContext.from_question(question).language == language


def test_old_state_without_language_and_date_only_refinement(monkeypatch):
    graph, _ = pipeline(monkeypatch)
    missing_period = replace(BASE_REQUEST, horizons=(), start_date=None, end_date=None)
    old_state = {
        "question": "Quelle est la performance du S&P 500 ?",
        "request": analysis_request_to_state(missing_period),
        "validation": validation_to_state(
            graph.strategist.validator.validate(missing_period)
        ),
    }
    # Seed the real saver with the historical state shape (no response_language).
    config = {"configurable": {"thread_id": "legacy"}}
    graph.graph.update_state(config, old_state, as_node="understand")
    stopped = graph.graph.invoke(None, config)
    assert "Précisez la date de début" in stopped["answer"]
    assert EquityStrategistGraph._context(old_state).language == "fr"
    assert (
        EquityStrategistGraph._context(
            {"question": "2025-01-01", "response_language": "fr"}
        ).language
        == "fr"
    )
    assert EquityStrategistGraph._context({"question": "2025-01-01"}).language == "en"


def test_result_defaults_and_raw_values_survive_json_roundtrip():
    value = 0.1234567890123
    item = PerformanceItem("TEST", "Test", value=value)
    period = PerformancePeriodResult(
        None,
        date(2025, 1, 1),
        date(2025, 2, 1),
        date(2025, 1, 1),
        date(2025, 2, 1),
        (item,),
    )
    assert period.comparison_items == ()
    result = PerformanceAnalysisResult(PerformanceMeasure.TOTAL, (period,))
    evidence = serialize_execution_evidence(
        _execution(StepExecutionResult(Capability.COMPARE_PERFORMANCE, result))
    )
    serialized = json.loads(json.dumps(evidence))["steps"][0]["result"]["periods"][0]
    assert serialized["comparison_items"] == []
    assert serialized["items"][0]["value"] == str(value)
    assert serialized["items"][0]["value_display"] == "12.35%"
    assert item.value == value


@pytest.mark.parametrize("language", ["fr", "en"])
def test_missing_currency_is_disclosed(language):
    items = (
        PerformanceItem("A", "Asset A", value=0.2),
        PerformanceItem("B", "Asset B", value=0.1, currency="EUR"),
    )
    period = PerformancePeriodResult(
        None,
        date(2025, 1, 1),
        date(2025, 2, 1),
        date(2025, 1, 1),
        date(2025, 2, 1),
        items,
    )
    result = PerformanceAnalysisResult(PerformanceMeasure.TOTAL, (period,))
    execution = _execution(StepExecutionResult(Capability.COMPARE_PERFORMANCE, result))
    evidence = serialize_execution_evidence(execution)["steps"][0]["result"]["periods"][
        0
    ]
    assert evidence["currency_metadata_complete"] is False
    answer = DeterministicInterpretation().interpret(
        execution, InterpretationContext(language=language)
    )
    assert (
        "Certaines devises ne sont pas renseignées"
        if language == "fr"
        else "Some currency metadata is unavailable"
    ) in answer


@pytest.mark.parametrize(
    "result,capability,label,value",
    [
        (
            VolatilityComparisonResult(
                date(2025, 1, 1),
                date(2025, 2, 1),
                252,
                (VolatilityItem("A", "Asset", 0.12345),),
            ),
            Capability.COMPARE_VOLATILITY,
            "Volatilité historique",
            "12.34%",
        ),
        (
            CorrelationAnalysisResult(
                date(2025, 1, 1),
                date(2025, 2, 1),
                (CorrelationItem("A", "Asset A", "B", "Asset B", 0.123456),),
            ),
            Capability.ANALYZE_CORRELATION,
            "Corrélation historique",
            "0.123",
        ),
        (
            DrawdownComparisonResult(
                date(2025, 1, 1),
                date(2025, 2, 1),
                (
                    DrawdownItem(
                        "A", "Asset", -0.12345, date(2025, 1, 2), date(2025, 1, 3), None
                    ),
                ),
            ),
            Capability.COMPARE_DRAWDOWN,
            "Baisse maximale",
            "-12.34%",
        ),
        (
            RankingResult(
                "volatility",
                date(2025, 1, 1),
                date(2025, 2, 1),
                (RankingItem(1, "A", "Asset", 0.12345),),
            ),
            Capability.RANK_VOLATILITY,
            "Volatilité historique",
            "12.34%",
        ),
    ],
)
def test_french_llm_failure_fallback_for_other_metrics(
    result, capability, label, value
):
    execution = _execution(StepExecutionResult(capability, result))
    answer = LLMInterpretation(client=FailingOpenAI()).interpret(
        execution, InterpretationContext(language="fr")
    )
    assert label in answer
    assert value in answer
    assert "2025-01-01" in answer and "2025-02-01" in answer
    assert "Dates effectives non renseignées" in answer


def test_volatility_top_n_keeps_comparison_evidence():
    from equity_strategist.domain.analysis_request import RankingDirection
    from equity_strategist.services.ranking_analysis import RankingAnalysisService
    from tests.test_ranking_analysis import FakeMarketDatasetService

    service = RankingAnalysisService(FakeMarketDatasetService())
    result = service.rank_volatility(
        ["LVMH", "Hermès", "ASML"],
        date(2020, 1, 1),
        date(2020, 1, 7),
        ranking_direction=RankingDirection.LOWEST,
        top_n=1,
    )
    assert len(result.items) == 1
    assert result.items[0].symbol == "MC.PA"
    assert [item.symbol for item in result.comparison_items] == [
        "MC.PA",
        "RMS.PA",
        "ASML.AS",
    ]
    evidence = serialize_execution_evidence(
        _execution(StepExecutionResult(Capability.RANK_VOLATILITY, result))
    )["steps"][0]["result"]
    assert len(evidence["items"]) == 1
    assert len(evidence["comparison_items"]) == 3
    assert evidence["comparison_items"][0] == evidence["items"][0]
    assert all(item["value_unit"] == "percent" for item in evidence["comparison_items"])


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan")])
def test_nonfinite_performance_evidence_is_rejected(value):
    from equity_strategist.domain.errors import InsufficientDataError

    with pytest.raises(InsufficientDataError):
        PerformanceItem("TEST", "Test", value=value)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("125.678", "125.68"),
        ("0.45", "0.45"),
        ("0.0045", "0.0045"),
        ("0.12345", "0.1234"),
        ("0.12355", "0.1236"),
        ("0.000012345", "0.00001234"),
        ("0.0000012345", "1.234E-6"),
        ("1e-1000", "1E-1000"),
        ("9.9999e-1000", "1E-999"),
    ],
)
@pytest.mark.parametrize("sign", ["", "-"])
def test_adaptive_prices_remain_nonzero(raw, expected, sign):
    price = Decimal(sign + raw)
    original = price.as_tuple()
    shown = display_value(price, "price")
    assert shown == sign + expected
    assert Decimal(shown) != 0
    assert price.as_tuple() == original


@pytest.mark.parametrize("rounding", ["ROUND_UP", "ROUND_DOWN", "ROUND_HALF_EVEN"])
def test_display_is_independent_of_callers_decimal_context(rounding):
    from decimal import Context, localcontext

    examples = [
        ("125.685", "price", "125.68"),
        ("125.695", "price", "125.70"),
        ("0.0045675", "price", "0.004568"),
        ("1e-1000", "price", "1E-1000"),
        ("-1e-1000", "price", "-1E-1000"),
        ("0.12345", "volatility", "12.34%"),
        ("0.12355", "performance", "12.36%"),
        ("0.12345", "excess_return", "12.34 pp"),
        ("0.1235", "correlation", "0.124"),
    ]
    with localcontext(Context(prec=2, rounding=rounding, Emin=-9, Emax=9)) as caller:
        for signal in caller.traps:
            caller.traps[signal] = True
        before = repr(caller)
        for raw, metric, expected in examples:
            assert display_value(raw, metric) == expected
        assert repr(caller) == before


@pytest.mark.parametrize(
    "question,assets,expected",
    [
        ("Compare DE and ET performance YTD", ("DE", "ET"), "en"),
        ("Compare la performance de DE et ET depuis janvier", ("DE", "ET"), "fr"),
        ("Compare LE and LA performance YTD", ("LE", "LA"), "en"),
        ("Compare la performance de LVMH et Hermès", (), "fr"),
        ("Compare La et Et performance YTD", ("La", "Et"), "fr"),
        ("Compare La and Et performance YTD", ("La", "Et"), "en"),
        ("COMPARE DE ET ET PERFORMANCE YTD", ("DE", "ET"), "fr"),
        ("COMPARE DE AND ET PERFORMANCE YTD", ("DE", "ET"), "en"),
        ("Compare de et et performance YTD", ("de", "et"), "fr"),
        ("Compare de and et performance YTD", ("DE", "ET"), "en"),
        ("WHAT IS THE PERFORMANCE?", (), "en"),
        ("QUELLE EST LA PERFORMANCE ?", (), "fr"),
    ],
)
def test_language_masks_only_known_references(question, assets, expected):
    assert (
        InterpretationContext.from_question(question, asset_references=assets).language
        == expected
    )
