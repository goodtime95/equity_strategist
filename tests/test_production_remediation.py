"""Offline regressions through the production composition and HTTP boundary."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from equity_strategist import app as composition
from equity_strategist.api.server import create_app
from equity_strategist.compute.performance import compute_total_performance
from equity_strategist.domain.analysis_request import (
    AnalysisHorizon,
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
    PerformanceMeasure,
)
from equity_strategist.domain.errors import InsufficientDataError
from equity_strategist.domain.market_series import MarketSeries, SeriesKind
from equity_strategist.domain.observations import DailyPriceObservation
from equity_strategist.strategists.graph import EquityStrategistGraph
from tests.test_api import AUTH
from tests.test_run_telemetry import RecordingRepository

BASE_REQUEST = AnalysisRequest(
    objective=AnalysisObjective.GET,
    metrics=(AnalysisMetric.PERFORMANCE,),
    assets=("S&P 500",),
    end_date=date(2025, 6, 30),
    horizons=(AnalysisHorizon.YEAR_TO_DATE,),
)


class FixedUnderstanding:
    def __init__(self, request):
        self.request = request

    def understand(self, question):
        return self.request


class MarketProvider:
    def __init__(self, bad_value="valid"):
        self.calls = []
        self.bad_value = bad_value

    def get_daily_prices(self, asset, start_date, end_date):
        self.calls.append((asset, start_date, end_date))
        final = {"^GSPC": "120", "^STOXX50E": "110", "RMS.PA": "130", "MC.PA": "105"}
        observations = []
        for day, value in (
            (date(2024, 12, 31), "100"),
            (date(2025, 6, 30), final[asset.symbol]),
        ):
            adjusted = Decimal(value)
            if self.bad_value != "valid":
                adjusted = None if self.bad_value is None else Decimal(self.bad_value)
            observations.append(
                DailyPriceObservation(
                    asset=asset,
                    date=day,
                    open=Decimal(value),
                    high=Decimal(value),
                    low=Decimal(value),
                    close=Decimal(value),
                    adjusted_close=adjusted,
                )
            )
        return observations


def pipeline(monkeypatch, request=BASE_REQUEST, bad_value="valid"):
    provider = MarketProvider(bad_value)
    monkeypatch.setattr(composition, "YahooFinanceProvider", lambda: provider)
    strategist = composition.build_equity_strategist()
    strategist.understanding = FixedUnderstanding(request)
    return EquityStrategistGraph(strategist), provider


def http_run(graph, question="What is the S&P 500 YTD performance?"):
    repository = RecordingRepository()
    with TestClient(
        create_app(lambda: graph, api_key="test-secret", repository=repository)
    ) as client:
        response = client.post(
            "/v1/chat",
            headers=AUTH,
            json={"question": question, "include_evidence": True},
        )
    return response, repository


@pytest.mark.parametrize(
    "bad_value", [None, "0", "-1", "Infinity", "-Infinity", "NaN", "1e-999", "1e999"]
)
def test_real_price_anomaly_maps_to_insufficient_data(monkeypatch, bad_value):
    graph, provider = pipeline(monkeypatch, bad_value=bad_value)
    response, repository = http_run(graph)
    assert provider.calls[0][0].symbol == "^GSPC"
    assert response.status_code == 422
    assert response.json()["error_category"] == "insufficient_data"
    assert repository.runs[0].error_category == "insufficient_data"
    assert repository.runs[0].error_metadata == {"stage": "execution"}


@pytest.mark.parametrize("benchmark", [None, "Euro Stoxx 50"])
def test_real_sp500_ytd_pipeline(monkeypatch, benchmark):
    request = replace(
        BASE_REQUEST,
        benchmark=benchmark,
        performance_measure=(
            PerformanceMeasure.EXCESS_RETURN if benchmark else PerformanceMeasure.TOTAL
        ),
    )
    graph, provider = pipeline(monkeypatch, request)
    response, _ = http_run(graph)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["request"]["horizons"] == ["ytd"]
    assert payload["request"]["start_date"] is None
    assert payload["request"]["benchmark"] == benchmark
    result = payload["evidence"]["steps"][0]["result"]
    assert result["price_field"] == "adjusted_close"
    assert result["measure"] == request.performance_measure.value
    period = result["periods"][0]
    assert period["horizon"] == "ytd"
    assert period["requested_start_date"] == "2025-01-01"
    assert period["requested_end_date"] == "2025-06-30"
    assert period["effective_start_date"] == "2024-12-31"
    assert period["effective_end_date"] == "2025-06-30"
    item = period["items"][0]
    assert item["symbol"] == "^GSPC"
    assert item["currency"] == "USD"
    assert item["observation_count"] == 2
    assert float(item["value"]) == pytest.approx(0.1 if benchmark else 0.2)
    assert float(item["total_performance"]) == pytest.approx(0.2)
    assert [(asset.symbol, start, end) for asset, start, end in provider.calls] == [
        (symbol, date(2024, 12, 22), date(2025, 6, 30))
        for symbol in (["^GSPC", "^STOXX50E"] if benchmark else ["^GSPC"])
    ]
    if benchmark:
        assert period["benchmark"]["symbol"] == "^STOXX50E"
        assert period["benchmark"]["currency"] == "EUR"
        assert float(period["benchmark"]["value"]) == pytest.approx(0.1)
        assert float(item["asset_performance"]) == pytest.approx(0.2)
        assert float(item["benchmark_performance"]) == pytest.approx(0.1)


@pytest.mark.parametrize("objective", [AnalysisObjective.GET, AnalysisObjective.RANK])
def test_equal_dates_clarify_before_provider(monkeypatch, objective):
    request = replace(
        BASE_REQUEST,
        objective=objective,
        horizons=(),
        start_date=BASE_REQUEST.end_date,
        assets=("Hermès", "LVMH")
        if objective == AnalysisObjective.RANK
        else BASE_REQUEST.assets,
    )
    graph, provider = pipeline(monkeypatch, request)
    response, _ = http_run(graph)
    assert response.status_code == 200
    assert response.json()["status"] == "needs_clarification"
    assert response.json()["validation"]["issue_codes"] == [
        "distinct_performance_dates_required"
    ]
    assert "two distinct" in response.json()["answer"]
    assert provider.calls == []


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan")])
def test_market_series_rejects_nonfinite_before_performance(value):
    with pytest.raises(InsufficientDataError):
        series = MarketSeries(
            "test",
            SeriesKind.PRICE,
            pd.Series([100, value], index=pd.to_datetime(["2025-01-01", "2025-01-02"])),
            "USD",
        )
        compute_total_performance(series)


def test_finite_input_overflow_cannot_produce_infinite_performance():
    series = MarketSeries(
        "test",
        SeriesKind.PRICE,
        pd.Series([1e-300, 1e300], index=pd.to_datetime(["2025-01-01", "2025-01-02"])),
        "USD",
    )
    with pytest.raises(InsufficientDataError):
        compute_total_performance(series)


def test_comparison_context_preserves_hermes_and_lvmh(monkeypatch):
    import json

    from equity_strategist.domain.analysis_request import RankingDirection
    from equity_strategist.interpretation.llm import LLMInterpretation
    from tests.test_llm_interpretation import FakeOpenAI

    request = replace(
        BASE_REQUEST,
        objective=AnalysisObjective.RANK,
        assets=("Hermès", "LVMH"),
        ranking_direction=RankingDirection.HIGHEST,
        top_n=1,
    )
    graph, provider = pipeline(monkeypatch, request)
    response, _ = http_run(
        graph, "Qui de Hermès ou LVMH a le mieux performé cette année ?"
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(provider.calls) == 2
    result = payload["evidence"]["steps"][0]["result"]
    assert result["top_n"] == 1
    assert result["ranking_direction"] == "highest"
    period = result["periods"][0]
    assert [item["symbol"] for item in period["items"]] == ["RMS.PA"]
    assert [item["symbol"] for item in period["comparison_items"]] == [
        "RMS.PA",
        "MC.PA",
    ]
    assert [item["rank"] for item in period["comparison_items"]] == [1, 2]
    assert [
        float(item["value"]) for item in period["comparison_items"]
    ] == pytest.approx([0.3, 0.05])
    assert [item["value_display"] for item in period["comparison_items"]] == [
        "30.00%",
        "5.00%",
    ]
    assert "Sélection" in payload["answer"]
    assert "Ensemble comparé" in payload["answer"]
    assert "Hermès" in payload["answer"] and "LVMH" in payload["answer"]
    assert "cours ajustés" in payload["answer"]

    client = FakeOpenAI("Hermès : 30.00%, LVMH : 5.00%.")
    graph.strategist.interpretation = LLMInterpretation(client=client)
    response, _ = http_run(
        graph, "Qui de Hermès ou LVMH a le mieux performé cette année ?"
    )
    evidence = json.loads(client.responses.calls[0]["input"])
    assert evidence["presentation_context"]["language"] == "fr"
    assert evidence["presentation_context"]["question"].startswith("Qui de Hermès")
    assert (
        evidence["steps"][0]["result"]["periods"][0]["comparison_items"]
        == period["comparison_items"]
    )
    assert "*_display" in client.responses.calls[0]["instructions"]
    assert "comparison_items" in client.responses.calls[0]["instructions"]


@pytest.mark.parametrize(
    "language,question,expected",
    [
        (
            "fr",
            "Quelle est la performance du S&P 500 cette année ?",
            "Période demandée",
        ),
        ("en", "What is the S&P 500 performance this year?", "Performance analysis"),
    ],
)
def test_language_reaches_llm_and_deterministic_fallback(
    monkeypatch, language, question, expected
):
    import json

    from equity_strategist.interpretation.llm import LLMInterpretation
    from tests.test_llm_interpretation import FakeOpenAI

    graph, _ = pipeline(monkeypatch)
    client = FakeOpenAI("")  # Empty output exercises the real deterministic fallback.
    graph.strategist.interpretation = LLMInterpretation(client=client)
    response, _ = http_run(graph, question)
    assert expected in response.json()["answer"]
    assert "20.00%" in response.json()["answer"]
    evidence = json.loads(client.responses.calls[0]["input"])
    assert evidence["presentation_context"] == {
        "question": question,
        "language": language,
    }
    assert (
        evidence["steps"][0]["result"]["periods"][0]["items"][0]["value_display"]
        == "20.00%"
    )


def test_native_currency_convention_reaches_synthesis(monkeypatch):
    import json

    from equity_strategist.interpretation.llm import LLMInterpretation
    from tests.test_llm_interpretation import FakeOpenAI

    graph, _ = pipeline(
        monkeypatch,
        replace(
            BASE_REQUEST,
            benchmark="Euro Stoxx 50",
            performance_measure=PerformanceMeasure.EXCESS_RETURN,
        ),
    )
    client = FakeOpenAI("")
    graph.strategist.interpretation = LLMInterpretation(client=client)
    response, _ = http_run(
        graph, "Quelle est la surperformance du S&P 500 contre Euro Stoxx 50 ?"
    )
    evidence = json.loads(client.responses.calls[0]["input"])
    period = evidence["steps"][0]["result"]["periods"][0]
    assert period["currency_convention"] == "native_returns_no_fx_conversion"
    assert period["currency_metadata_complete"] is True
    assert period["items"][0]["value_display"] == "10.00 pp"
    assert period["items"][0]["value_unit"] == "percentage_points"
    assert period["items"][0]["asset_performance_display"] == "20.00%"
    assert period["benchmark"]["value_display"] == "10.00%"
    answer = response.json()["answer"]
    assert "devises natives" in answer
    assert "sans conversion ni effet de change" in answer
    assert "ce n’est pas une surperformance dans une devise commune" in answer


@pytest.mark.parametrize("french", [False, True])
def test_known_unsupported_blockers_precede_missing_period(monkeypatch, french):
    request = replace(
        BASE_REQUEST,
        objective=AnalysisObjective.RANK,
        metrics=(AnalysisMetric.DRAWDOWN,),
        assets=("Hermès", "LVMH"),
        horizons=(),
        end_date=None,
        constraints=("rolling window",),
        unresolved=("Eurostoxx: index or constituents?",),
    )
    graph, provider = pipeline(monkeypatch, request)
    response, _ = http_run(
        graph,
        "Classe les actifs par drawdown" if french else "Rank the assets by drawdown",
    )
    payload = response.json()
    assert payload["status"] == "unsupported"
    assert payload["validation"]["issue_codes"] == [
        "constraints_unsupported",
        "analysis_combination_unsupported",
        "unresolved_semantics",
    ]
    assert "missing_start_date" not in payload["validation"]["issue_codes"]
    assert "missing_end_date" not in payload["validation"]["issue_codes"]
    assert ("pas encore prise en charge" if french else "not supported yet") in payload[
        "answer"
    ]
    assert ("classement + baisse maximale" if french else "rank + drawdown") in payload[
        "answer"
    ]
    assert "Eurostoxx" in payload["answer"]
    assert provider.calls == []


def test_french_equal_period_clarification(monkeypatch):
    graph, provider = pipeline(
        monkeypatch,
        replace(BASE_REQUEST, horizons=(), start_date=BASE_REQUEST.end_date),
    )
    response, _ = http_run(graph, "Quelle performance hier ?")
    assert response.json()["status"] == "needs_clarification"
    assert "deux dates ou observations distinctes" in response.json()["answer"]
    assert provider.calls == []


def test_valid_explicit_period_remains_executable(monkeypatch):
    graph, _ = pipeline(
        monkeypatch, replace(BASE_REQUEST, horizons=(), start_date=date(2025, 1, 1))
    )
    response, _ = http_run(graph)
    assert response.json()["status"] == "success"
    period = response.json()["evidence"]["steps"][0]["result"]["periods"][0]
    assert period["horizon"] is None
    assert period["effective_start_date"] == "2024-12-31"
    assert float(period["items"][0]["value"]) == pytest.approx(0.2)


def test_generic_programming_value_error_remains_internal(monkeypatch):
    graph, provider = pipeline(monkeypatch)

    def broken(**kwargs):
        raise ValueError("programming bug")

    monkeypatch.setattr(provider, "get_daily_prices", broken)
    response, repository = http_run(graph)
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
    assert "programming bug" not in response.text
    assert repository.runs[0].error_category == "internal_error"


def test_empty_provider_data_is_insufficient(monkeypatch):
    graph, provider = pipeline(monkeypatch)
    monkeypatch.setattr(provider, "get_daily_prices", lambda **kwargs: [])
    response, _ = http_run(graph)
    assert response.status_code == 422
    assert response.json()["error_category"] == "insufficient_data"


@pytest.mark.parametrize("bad_value", [None, "0", "NaN", "Infinity", "-Infinity"])
def test_point_price_has_same_adjusted_data_policy(monkeypatch, bad_value):
    request = replace(
        BASE_REQUEST,
        metrics=(AnalysisMetric.PRICE,),
        end_date=None,
        horizons=(),
        target_date=date(2025, 6, 30),
    )
    graph, _ = pipeline(monkeypatch, request, bad_value)
    response, _ = http_run(graph, "What is the S&P 500 price?")
    assert response.status_code == 422
    assert response.json()["error_category"] == "insufficient_data"


def test_duplicate_provider_dates_are_insufficient_not_programming_error(monkeypatch):
    graph, provider = pipeline(monkeypatch)
    original = provider.get_daily_prices

    def duplicate(**kwargs):
        observations = original(**kwargs)
        return observations + [observations[-1]]

    monkeypatch.setattr(provider, "get_daily_prices", duplicate)
    response, _ = http_run(graph)
    assert response.status_code == 422
    assert response.json()["error_category"] == "insufficient_data"


def test_annualized_overflow_is_insufficient():
    from equity_strategist.compute.performance import compute_annualized_performance

    series = MarketSeries(
        "test",
        SeriesKind.PRICE,
        pd.Series([1, 1e300], index=pd.to_datetime(["2025-01-01", "2025-01-02"])),
        "USD",
    )
    with pytest.raises(InsufficientDataError):
        compute_annualized_performance(series)


def test_unrepresentable_relative_benchmark_is_data_failure(monkeypatch):
    graph, provider = pipeline(
        monkeypatch,
        replace(
            BASE_REQUEST,
            benchmark="Euro Stoxx 50",
            performance_measure=PerformanceMeasure.RELATIVE,
        ),
    )
    original = provider.get_daily_prices

    def tiny_benchmark(**kwargs):
        observations = original(**kwargs)
        if kwargs["asset"].symbol == "^STOXX50E":
            observations[-1] = replace(
                observations[-1], adjusted_close=Decimal("1e-300")
            )
        return observations

    monkeypatch.setattr(provider, "get_daily_prices", tiny_benchmark)
    response, _ = http_run(graph)
    assert response.status_code == 422
    assert response.json()["error_category"] == "insufficient_data"


@pytest.mark.parametrize(
    "raw,display",
    [
        ("125.678", "125.68"),
        ("0.45", "0.45"),
        ("0.0045", "0.0045"),
        ("1e-1000", "1E-1000"),
    ],
)
@pytest.mark.parametrize(
    "language,question,label",
    [
        ("en", "What is the price of PENNY?", "was"),
        ("fr", "Quel est le prix de PENNY ?", "Cours"),
    ],
)
def test_adaptive_price_public_evidence_llm_and_fallback(
    monkeypatch, raw, display, language, question, label
):
    import json

    from equity_strategist.asset_registry.registry import AssetRegistry
    from equity_strategist.domain.asset import Asset
    from equity_strategist.interpretation.llm import LLMInterpretation
    from tests.test_llm_interpretation import FakeOpenAI

    asset = Asset("PENNY", "Synthetic equity", currency="USD")
    monkeypatch.setattr(
        composition, "build_default_asset_registry", lambda: AssetRegistry([asset])
    )
    request = replace(
        BASE_REQUEST,
        assets=("PENNY",),
        metrics=(AnalysisMetric.PRICE,),
        horizons=(),
        end_date=None,
        target_date=date(2025, 6, 30),
    )
    graph, provider = pipeline(monkeypatch, request)
    price = Decimal(raw)

    def prices(asset, start_date, end_date):
        return [
            DailyPriceObservation(
                asset, end_date, price, price, price, price, adjusted_close=price
            )
        ]

    monkeypatch.setattr(provider, "get_daily_prices", prices)
    client = FakeOpenAI("")
    graph.strategist.interpretation = LLMInterpretation(client=client)
    response, _ = http_run(graph, question)
    assert response.status_code == 200
    payload = response.json()
    evidence = payload["evidence"]["steps"][0]["result"]
    assert evidence["price"] == str(price)
    assert evidence["price_display"] == display
    assert Decimal(evidence["price_display"]) != 0
    assert label in payload["answer"]
    assert display + " USD" in payload["answer"]
    llm_input = json.loads(client.responses.calls[0]["input"])
    assert llm_input["steps"][0]["result"] == evidence
    assert llm_input["presentation_context"] == {
        "question": question,
        "language": language,
    }


@pytest.mark.parametrize(
    "question,assets,expected",
    [
        ("Compare DE and ET performance YTD", ("DE", "ET"), "Performance analysis"),
        (
            "Compare la performance de DE et ET depuis janvier",
            ("DE", "ET"),
            "Performance totale",
        ),
        ("Compare LE and LA performance YTD", ("LE", "LA"), "Performance analysis"),
        ("Compare La et Et performance YTD", ("La", "Et"), "Performance totale"),
        ("Compare La and Et performance YTD", ("La", "Et"), "Performance analysis"),
        ("COMPARE DE ET ET PERFORMANCE YTD", ("DE", "ET"), "Performance totale"),
        ("COMPARE DE AND ET PERFORMANCE YTD", ("DE", "ET"), "Performance analysis"),
    ],
)
def test_public_language_uses_intent_assets_without_extra_provider_calls(
    monkeypatch, question, assets, expected
):
    from equity_strategist.asset_registry.registry import AssetRegistry
    from equity_strategist.domain.asset import Asset

    monkeypatch.setattr(
        composition,
        "build_default_asset_registry",
        lambda: AssetRegistry(
            [Asset(symbol, symbol, currency="USD") for symbol in assets]
        ),
    )
    graph, provider = pipeline(
        monkeypatch,
        replace(BASE_REQUEST, objective=AnalysisObjective.COMPARE, assets=assets),
    )
    calls = []

    def prices(asset, start_date, end_date):
        calls.append((asset.symbol, start_date, end_date))
        return [
            DailyPriceObservation(
                asset,
                day,
                Decimal(value),
                Decimal(value),
                Decimal(value),
                Decimal(value),
                adjusted_close=Decimal(value),
            )
            for day, value in [(date(2024, 12, 31), "100"), (end_date, "110")]
        ]

    monkeypatch.setattr(provider, "get_daily_prices", prices)
    response, _ = http_run(graph, question)
    assert response.status_code == 200
    assert expected in response.json()["answer"]
    assert calls == [
        (symbol, date(2024, 12, 22), date(2025, 6, 30)) for symbol in assets
    ]
    # The standalone entry point receives the same available intent references.
    assert expected in graph.strategist.answer(question)
    expected_calls = [
        (symbol, date(2024, 12, 22), date(2025, 6, 30)) for symbol in assets
    ]
    assert calls == expected_calls * 2

    # The synthesis context must agree with both deterministic entry points.
    import json

    from equity_strategist.interpretation.llm import LLMInterpretation
    from tests.test_llm_interpretation import FakeOpenAI

    client = FakeOpenAI("")
    graph.strategist.interpretation = LLMInterpretation(client=client)
    response, _ = http_run(graph, question)
    assert response.status_code == 200
    assert expected in response.json()["answer"]
    context = json.loads(client.responses.calls[0]["input"])["presentation_context"]
    assert context["language"] == ("en" if expected == "Performance analysis" else "fr")
    assert calls == expected_calls * 3


def test_public_clarification_retains_french_and_old_state_defaults(monkeypatch):
    from equity_strategist.api.server import create_app
    from equity_strategist.strategists.graph_state import (
        analysis_request_to_state,
        validation_to_state,
    )

    missing = replace(BASE_REQUEST, horizons=(), end_date=None)
    graph, provider = pipeline(monkeypatch, missing)

    class Understanding:
        def understand(self, question):
            return missing

        def refine(self, previous_request, clarification):
            return BASE_REQUEST

    graph.strategist.understanding = Understanding()
    # Historical shape without response_language must still load in the API.
    old = {
        "question": "What is the performance?",
        "request": analysis_request_to_state(missing),
        "validation": validation_to_state(graph.strategist.validator.validate(missing)),
    }
    graph.graph.update_state(
        {"configurable": {"thread_id": "old"}}, old, as_node="understand"
    )
    with TestClient(create_app(lambda: graph, api_key="test-secret")) as client:
        first = client.post(
            "/v1/chat",
            headers=AUTH,
            json={
                "thread_id": "fr",
                "question": "Quelle est la performance du S&P 500 ?",
            },
        )
        assert first.json()["status"] == "needs_clarification"
        assert provider.calls == []
        second = client.post(
            "/v1/chat", headers=AUTH, json={"thread_id": "fr", "question": "2025-06-30"}
        )
        assert second.status_code == 200
        assert "Période demandée" in second.json()["answer"]
        legacy = client.post(
            "/v1/chat",
            headers=AUTH,
            json={"thread_id": "old", "question": "2025-06-30"},
        )
        assert legacy.status_code == 200
        assert "Performance analysis" in legacy.json()["answer"]


def test_provider_failure_remains_502(monkeypatch):
    from equity_strategist.domain.errors import ProviderFailure

    graph, provider = pipeline(monkeypatch)

    def fail(**kwargs):
        raise ProviderFailure("private payload")

    monkeypatch.setattr(provider, "get_daily_prices", fail)
    response, repository = http_run(graph)
    assert response.status_code == 502
    assert response.json()["error_category"] == "provider_failure"
    assert repository.runs[0].error_category == "provider_failure"
    assert "private payload" not in response.text
