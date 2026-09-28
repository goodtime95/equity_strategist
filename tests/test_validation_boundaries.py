"""Untrusted understanding and locally decidable universe failures, offline."""

import json
from dataclasses import replace
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from equity_strategist.api.server import create_app
from equity_strategist.domain.analysis_request import AmbiguityScope, AnalysisObjective
from equity_strategist.domain.errors import ProviderFailure
from equity_strategist.domain.universe import Universe, UniverseType
from equity_strategist.services.ranking_analysis import RankingAnalysisService
from equity_strategist.strategists.graph_state import analysis_request_to_state
from equity_strategist.strategists.validator import AnalysisRequestValidator
from equity_strategist.understanding.llm import (
    ANALYSIS_REQUEST_SCHEMA,
    LLMUnderstanding,
)
from equity_strategist.universe_registry.registry import UniverseRegistry
from tests.test_api import AUTH
from tests.test_production_remediation import BASE_REQUEST, http_run, pipeline
from tests.test_run_telemetry import RecordingRepository


def llm_payload(**updates):
    state = analysis_request_to_state(BASE_REQUEST)
    payload = {key: state[key] for key in ANALYSIS_REQUEST_SCHEMA["properties"]}
    payload.update(updates)
    return payload


def fake_llm(payloads):
    responses = iter(payloads)
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(output_text=json.dumps(next(responses)))

    return LLMUnderstanding(
        client=SimpleNamespace(responses=SimpleNamespace(create=create))
    ), calls


def assert_stopped(response, snapshot, status, stage="understanding"):
    assert response.status_code == 200
    assert response.json()["status"] == status
    assert snapshot.request_id == UUID(response.json()["request_id"])
    assert snapshot.outcome_status == status
    assert snapshot.error_category is None
    assert snapshot.planned_capabilities == []
    stages = snapshot.telemetry_json["stages"]
    assert {s["stage"] for s in stages} >= {
        stage,
        "validation",
        "interpretation",
        "serialization",
    }
    assert not {"planning", "execution"} & {s["stage"] for s in stages}
    assert all(not s["failed"] for s in stages)


@pytest.mark.parametrize("refinement", [False, True])
@pytest.mark.parametrize(
    "scopes,unresolved,expected",
    [
        (["instrument"], [], ["instrument"]),
        (["instrument", "period"], [], ["instrument", "period"]),
        (["instrument", "instrument"], [], ["instrument"]),
        (["future_scope"], [], ["unknown"]),
        (["future_scope", "period"], [], ["unknown", "period"]),
        (
            ["future_scope", "period", "future_scope"],
            ["Which period?"],
            ["unknown", "period"],
        ),
        ([], ["Which benchmark?"], []),
        ([], [" "], ["unknown"]),
        (["instrument"], [" "], ["unknown"]),
    ],
)
def test_untrusted_scopes_through_http(
    monkeypatch, refinement, scopes, unresolved, expected
):
    graph, provider = pipeline(monkeypatch)
    payload = llm_payload(ambiguity_scopes=scopes, unresolved=unresolved)
    payloads = [payload]
    if refinement:
        payloads.insert(
            0,
            llm_payload(
                unresolved=["Which instrument?"], ambiguity_scopes=["instrument"]
            ),
        )
    graph.strategist.understanding, calls = fake_llm(payloads)

    def forbidden(*args, **kwargs):
        pytest.fail("An unresolved model output must not reach planning or providers")

    monkeypatch.setattr(graph.strategist.planner, "plan", forbidden)
    monkeypatch.setattr(provider, "get_daily_prices", forbidden)
    monkeypatch.setattr(
        graph.strategist.executor.universe_constituent_service,
        "get_constituents",
        forbidden,
    )
    repository = RecordingRepository()
    with TestClient(
        create_app(lambda: graph, api_key="test-secret", repository=repository)
    ) as client:
        responses = [
            client.post(
                "/v1/chat",
                headers=AUTH,
                json={
                    "thread_id": "scopes",
                    "question": "What is the YTD performance?",
                },
            )
        ]
        if refinement:
            responses.append(
                client.post(
                    "/v1/chat",
                    headers=AUTH,
                    json={"thread_id": "scopes", "question": "Use the S&P 500"},
                )
            )
    for index, (response, snapshot) in enumerate(
        zip(responses, repository.runs, strict=True)
    ):
        assert_stopped(
            response,
            snapshot,
            "needs_clarification",
            "refinement" if index else "understanding",
        )
        codes = response.json()["validation"]["issue_codes"]
        if refinement and index == 0:
            assert codes == ["unresolved_semantics"]
        elif unresolved == [" "]:
            assert codes == ["invalid_llm_ambiguity_metadata"]
        elif not unresolved:
            assert codes == [f"clarify_{scope}" for scope in expected]
        else:
            assert codes == ["unresolved_semantics"] + (
                ["clarify_unknown"] if "future_scope" in scopes else []
            )
        assert "ambiguity_scopes" not in response.json()["request"]
        assert response.json()["request"]["metrics"] == ["performance"]
        assert response.json()["request"]["horizons"] == ["ytd"]
    state = graph.graph.get_state({"configurable": {"thread_id": "scopes"}}).values
    assert state["request"]["ambiguity_scopes"] == expected
    assert state["request"]["unresolved"]
    assert provider.calls == []
    if refinement:
        assert json.loads(calls[1]["input"])["previous_request"][
            "ambiguity_scopes"
        ] == ["instrument"]
        assert responses[0].json()["request_id"] != responses[1].json()["request_id"]
    if "future_scope" in scopes:
        assert "could not be classified" in responses[-1].json()["answer"]
        assert "future_scope" not in responses[-1].text
    elif not unresolved:
        assert "Which instrument or index" in responses[-1].json()["answer"]


def test_resolved_llm_payload_is_ready():
    payload = llm_payload()
    understanding, _ = fake_llm([payload])
    request = understanding.understand("S&P 500 YTD")
    assert request.ambiguity_scopes == ()
    assert request.unresolved == ()
    assert AnalysisRequestValidator().validate(request).is_ready


def test_multiscopes_refinement_retains_remaining_ambiguity():
    understanding, _ = fake_llm(
        [
            llm_payload(
                ambiguity_scopes=["instrument", "period"],
                unresolved=["Which instrument and period?"],
            ),
            llm_payload(
                ambiguity_scopes=["period", "period"], unresolved=["Which period?"]
            ),
            llm_payload(),
        ]
    )
    initial = understanding.understand("performance")
    refined = understanding.refine(initial, "S&P 500")
    assert refined.ambiguity_scopes == (AmbiguityScope.PERIOD,)
    assert refined.unresolved == ("Which period?",)
    assert not AnalysisRequestValidator().validate(refined).is_ready
    resolved = understanding.refine(refined, "YTD")
    assert AnalysisRequestValidator().validate(resolved).is_ready


def test_unrelated_understanding_value_error_remains_500(monkeypatch):
    graph, provider = pipeline(monkeypatch)
    graph.strategist.understanding, _ = fake_llm(
        [llm_payload(start_date="2026-09-24", end_date="2025-01-01")]
    )
    response, repository = http_run(graph)
    assert response.status_code == 500
    assert repository.runs[0].error_metadata == {"stage": "understanding"}
    assert provider.calls == []


def universe_catalog(heterogeneous=False):
    single = Universe("Single", UniverseType.STATIC, ("LVMH",), aliases=("shared",))
    other = replace(single, name="Other")
    if heterogeneous:
        other = replace(other, name="Viable", asset_queries=("LVMH", "Hermès"))
    return UniverseRegistry([single, other])


def install_catalog(graph, registry):
    graph.strategist.validator.universe_registry = registry
    graph.strategist.executor.universe_constituent_service.universe_registry = registry


@pytest.mark.parametrize("reference", ["shared", "Single"])
@pytest.mark.parametrize("language", ["fr", "en"])
def test_locally_impossible_universe_stops_http(monkeypatch, reference, language):
    request = replace(
        BASE_REQUEST, assets=(), universe=reference, objective=AnalysisObjective.RANK
    )
    graph, provider = pipeline(monkeypatch, request)
    install_catalog(graph, universe_catalog())

    def forbidden(*args, **kwargs):
        pytest.fail(
            "Locally impossible universe reached planning or constituent lookup"
        )

    monkeypatch.setattr(graph.strategist.planner, "plan", forbidden)
    monkeypatch.setattr(
        graph.strategist.executor.universe_constituent_service,
        "get_constituents",
        forbidden,
    )
    response, repository = http_run(
        graph,
        "Classe les actions selon leur performance"
        if language == "fr"
        else "Rank the stocks by performance",
    )
    assert_stopped(response, repository.runs[0], "unsupported")
    assert response.json()["validation"]["issue_codes"] == [
        "universe_ranking_asset_count"
    ]
    assert (
        "au moins deux actifs" if language == "fr" else "at least two assets"
    ) in response.json()["answer"]
    assert provider.calls == []


@pytest.mark.parametrize("selection", ["Single", "Viable"])
def test_heterogeneous_alias_conversation(monkeypatch, selection):
    request = replace(
        BASE_REQUEST, assets=(), universe="shared", objective=AnalysisObjective.RANK
    )
    graph, provider = pipeline(monkeypatch, request)
    install_catalog(graph, universe_catalog(heterogeneous=True))
    first_payload = llm_payload(objective="rank", assets=[], universe="shared")
    second_payload = dict(first_payload, universe=selection)
    graph.strategist.understanding, calls = fake_llm([first_payload, second_payload])
    repository = RecordingRepository()
    with TestClient(
        create_app(lambda: graph, api_key="test-secret", repository=repository)
    ) as client:
        first = client.post(
            "/v1/chat",
            headers=AUTH,
            json={
                "thread_id": "universes",
                "question": "Classe les actions de cet univers",
            },
        )
        assert_stopped(first, repository.runs[0], "needs_clarification")
        assert "Viable" in first.json()["answer"]
        assert "Single" not in first.json()["answer"]
        assert provider.calls == []
        second = client.post(
            "/v1/chat",
            headers=AUTH,
            json={"thread_id": "universes", "question": selection},
        )
    assert len(calls) == 2
    assert "previous_request" in json.loads(calls[1]["input"])
    if selection == "Single":
        assert_stopped(second, repository.runs[1], "unsupported", "refinement")
        assert provider.calls == []
    else:
        assert second.status_code == 200
        assert second.json()["status"] == "success"
        assert repository.runs[1].planned_capabilities == ["rank_performance"]
        assert len(provider.calls) == 2


@pytest.mark.parametrize("count", [0, 1])
def test_ranking_service_rejects_insufficient_cardinality_without_data(count):
    service = RankingAnalysisService(market_dataset_service=None)
    with pytest.raises(ValueError, match="at least two assets"):
        service.rank_performance_for_assets(
            (object(),) * count, None, BASE_REQUEST.end_date
        )
    with pytest.raises(ValueError, match="at least two assets"):
        service.rank_performance(["LVMH"] * count, None, BASE_REQUEST.end_date)


def test_empty_static_universe_remains_invalid_domain_object():
    with pytest.raises(ValueError, match="static universe requires assets"):
        Universe("Empty", UniverseType.STATIC, ())


def test_dynamic_universe_provider_failure_remains_502(monkeypatch):
    request = replace(
        BASE_REQUEST, assets=(), universe="CAC 40", objective=AnalysisObjective.RANK
    )
    graph, provider = pipeline(monkeypatch, request)
    assert graph.strategist.validator.validate(request).is_ready

    def unavailable(identifier):
        raise ProviderFailure("private upstream failure")

    constituent_provider = (
        graph.strategist.executor.universe_constituent_service.universe_providers[
            "euronext"
        ]
    )
    monkeypatch.setattr(constituent_provider, "get_constituents", unavailable)
    response, repository = http_run(graph)
    assert response.status_code == 502
    assert repository.runs[0].error_category == "provider_failure"
    assert provider.calls == []


def test_orphan_scope_refinement_from_legacy_checkpoint(monkeypatch):
    graph, provider = pipeline(monkeypatch)
    pending = analysis_request_to_state(
        replace(BASE_REQUEST, unresolved=("Which instrument?",))
    )
    del pending["ambiguity_scopes"]
    graph.graph.update_state(
        {"configurable": {"thread_id": "legacy"}},
        {
            "question": "Performance?",
            "request": pending,
            "validation": {
                "status": "needs_clarification",
                "issues": ["Which instrument?"],
            },
        },
        as_node="understand",
    )
    graph.strategist.understanding, calls = fake_llm(
        [llm_payload(ambiguity_scopes=["instrument"], unresolved=[])]
    )
    repository = RecordingRepository()
    with TestClient(
        create_app(lambda: graph, api_key="test-secret", repository=repository)
    ) as client:
        response = client.post(
            "/v1/chat",
            headers=AUTH,
            json={"thread_id": "legacy", "question": "S&P 500"},
        )
    assert_stopped(response, repository.runs[0], "needs_clarification", "refinement")
    previous = json.loads(calls[0]["input"])["previous_request"]
    assert previous["ambiguity_scopes"] == []
    assert previous["unresolved"] == ["Which instrument?"]
    assert provider.calls == []


@pytest.mark.parametrize("metric", ["performance", "volatility", "drawdown"])
def test_scoped_alias_retains_operation_priority(metric):
    from equity_strategist.domain.analysis_request import AnalysisMetric

    request = replace(
        BASE_REQUEST,
        objective=AnalysisObjective.RANK,
        assets=(),
        universe="shared",
        metrics=(AnalysisMetric(metric),),
        unresolved=("Which instrument?",),
        ambiguity_scopes=(AmbiguityScope.INSTRUMENT,),
    )
    result = AnalysisRequestValidator(universe_catalog(heterogeneous=True)).validate(
        request
    )
    expected = {
        "performance": ("needs_clarification", "ambiguous_universe"),
        "volatility": ("unsupported", "universe_capability_unsupported"),
        "drawdown": ("unsupported", "analysis_combination_unsupported"),
    }
    status, code = expected[metric]
    assert result.status.value == status
    assert code in result.issue_codes
    assert "performance_reference_ambiguous" not in result.issue_codes


def test_independent_limit_precedes_viable_alias_clarification():
    request = replace(
        BASE_REQUEST,
        objective=AnalysisObjective.RANK,
        assets=(),
        universe="shared",
        constraints=("currency conversion",),
    )
    result = AnalysisRequestValidator(universe_catalog(heterogeneous=True)).validate(
        request
    )
    assert result.status.value == "unsupported"
    assert result.issue_codes == ("constraints_unsupported",)


@pytest.mark.parametrize("refinement", [False, True])
@pytest.mark.parametrize(
    "key,value,missing",
    [
        ("unresolved", None, True),
        ("unresolved", None, False),
        ("unresolved", [3], False),
        ("ambiguity_scopes", None, False),
        ("ambiguity_scopes", [["instrument"]], False),
        ("ambiguity_scopes", {}, False),
        ("unresolved", "period", False),
        ("ambiguity_scopes", None, True),
        ("ambiguity_scopes", [" "], False),
        ("unresolved", [" "], False),
    ],
)
def test_malformed_ambiguity_metadata_http(
    monkeypatch, refinement, key, value, missing
):
    graph, provider = pipeline(monkeypatch)
    payload = llm_payload(**{key: value})
    if missing:
        del payload[key]
    payloads = [payload]
    if refinement:
        payloads.insert(0, llm_payload(ambiguity_scopes=["instrument"]))
    graph.strategist.understanding, _ = fake_llm(payloads)

    def forbidden(*args, **kwargs):
        pytest.fail("Malformed metadata reached planning, execution or a provider")

    monkeypatch.setattr(graph.strategist.planner, "plan", forbidden)
    monkeypatch.setattr(graph.strategist.executor, "execute", forbidden)
    monkeypatch.setattr(provider, "get_daily_prices", forbidden)
    monkeypatch.setattr(
        graph.strategist.executor.universe_constituent_service,
        "get_constituents",
        forbidden,
    )
    repository = RecordingRepository()
    with TestClient(
        create_app(lambda: graph, api_key="test-secret", repository=repository)
    ) as client:
        if refinement:
            first = client.post(
                "/v1/chat",
                headers=AUTH,
                json={"thread_id": "invalid", "question": "Performance YTD ?"},
            )
            assert_stopped(first, repository.runs[0], "needs_clarification")
        response = client.post(
            "/v1/chat",
            headers=AUTH,
            json={"thread_id": "invalid", "question": "S&P 500"},
        )
    assert_stopped(
        response,
        repository.runs[-1],
        "needs_clarification",
        "refinement" if refinement else "understanding",
    )
    assert response.json()["validation"]["issue_codes"] == [
        "invalid_llm_ambiguity_metadata"
    ]
    assert provider.calls == []
    if refinement:
        assert first.json()["request_id"] != response.json()["request_id"]


@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("scope", [scope.value for scope in AmbiguityScope] + [None])
def test_synthetic_questions_localized_with_conversation_fallback(
    monkeypatch, language, scope
):
    graph, provider = pipeline(monkeypatch)
    payload = llm_payload(ambiguity_scopes=[scope] if scope else None)
    graph.strategist.understanding, _ = fake_llm([payload, payload])
    repository = RecordingRepository()
    with TestClient(
        create_app(lambda: graph, api_key="test-secret", repository=repository)
    ) as client:
        for index, question in enumerate(
            [
                "Quelle est la performance de cet actif ?"
                if language == "fr"
                else "What is the performance of this asset?",
                "S&P 500",
            ]
        ):
            response = client.post(
                "/v1/chat",
                headers=AUTH,
                json={"thread_id": "localization", "question": question},
            )
            assert_stopped(
                response,
                repository.runs[index],
                "needs_clarification",
                "refinement" if index else "understanding",
            )
            code = f"clarify_{scope}" if scope else "invalid_llm_ambiguity_metadata"
            from equity_strategist.interpretation.localization import (
                SYNTHETIC_QUESTIONS,
            )

            expected = SYNTHETIC_QUESTIONS[code][0 if language == "fr" else 1]
            payload_out = response.json()
            assert expected in payload_out["answer"]
            assert payload_out["request"]["unresolved"] == [expected]
            assert payload_out["validation"]["issues"] == [expected]
            assert code not in payload_out["answer"]
            assert payload_out["validation"]["issue_codes"] == [code]
    assert provider.calls == []


@pytest.mark.parametrize(
    "references,reference,other,explicit,status,code",
    [
        (
            ("LVMH", "LVMH"),
            "Broken",
            None,
            False,
            "unsupported",
            "universe_ranking_duplicate_assets",
        ),
        (
            ("LVMH", " lvmh "),
            " broken ",
            None,
            False,
            "unsupported",
            "universe_ranking_duplicate_assets",
        ),
        (("LVMH", "Hermès"), "Broken", None, False, "success", None),
        (
            ("LVMH", "LVMH"),
            "shared",
            ("LVMH", "Hermès"),
            False,
            "needs_clarification",
            "ambiguous_universe",
        ),
        (
            ("LVMH", "LVMH"),
            "shared",
            ("LVMH", " lvmh "),
            False,
            "unsupported",
            "universe_ranking_duplicate_assets",
        ),
        (
            ("LVMH", " lvmh "),
            None,
            None,
            True,
            "needs_clarification",
            "duplicate_asset",
        ),
    ],
)
def test_duplicate_ranking_references_stop_before_planning(
    monkeypatch, references, reference, other, explicit, status, code
):
    request = replace(
        BASE_REQUEST,
        objective=AnalysisObjective.RANK,
        assets=references if explicit else (),
        universe=reference,
    )
    graph, provider = pipeline(monkeypatch, request)
    broken = Universe("Broken", UniverseType.STATIC, references, aliases=("shared",))
    universes = [broken]
    if other:
        universes.append(replace(broken, name="Other", asset_queries=other))
    install_catalog(graph, UniverseRegistry(universes))
    if status != "success":

        def forbidden(*args, **kwargs):
            pytest.fail("Invalid ranking reached planning, execution or providers")

        monkeypatch.setattr(graph.strategist.planner, "plan", forbidden)
        monkeypatch.setattr(graph.strategist.executor, "execute", forbidden)
        monkeypatch.setattr(provider, "get_daily_prices", forbidden)
        monkeypatch.setattr(
            graph.strategist.executor.universe_constituent_service,
            "get_constituents",
            forbidden,
        )
    response, repository = http_run(graph, "Classe les actions selon la performance")
    assert response.status_code == 200
    assert response.json()["status"] == status
    if code:
        assert_stopped(response, repository.runs[0], status)
        assert response.json()["validation"]["issue_codes"] == [code]
        assert provider.calls == []
        if code == "ambiguous_universe":
            assert "Other" in response.json()["answer"]
            assert "Broken" not in response.json()["answer"]
        elif code == "universe_ranking_duplicate_assets":
            assert "en double" in response.json()["answer"]
    else:
        assert len(provider.calls) == 2


def test_service_duplicate_precondition_without_data():
    from equity_strategist.domain.asset import Asset

    service = RankingAnalysisService(market_dataset_service=None)
    for operation in (service.rank_performance, service.rank_volatility):
        with pytest.raises(ValueError, match="duplicate asset references"):
            operation(["LVMH", " lvmh "], None, BASE_REQUEST.end_date)
    with pytest.raises(ValueError, match="duplicate asset references"):
        service.rank_performance_for_assets(
            (Asset("MC.PA"), Asset(" mc.pa ")), None, BASE_REQUEST.end_date
        )


def test_crossed_aliases_http_two_refinements(monkeypatch):
    first = Universe(
        "Alpha",
        UniverseType.STATIC,
        ("LVMH", "Hermès"),
        aliases=("shared", "Beta"),
    )
    registry = UniverseRegistry(
        [
            first,
            replace(first, name="Beta", aliases=("shared", "Alpha")),
        ]
    )
    graph, provider = pipeline(monkeypatch)
    install_catalog(graph, registry)
    graph.strategist.understanding, calls = fake_llm(
        [
            llm_payload(objective="rank", assets=[], universe="shared"),
            llm_payload(
                objective="rank",
                assets=[],
                universe=" Alpha ",
                ambiguity_scopes=["period"],
            ),
            llm_payload(objective="rank", assets=[], universe=" beta "),
        ]
    )
    repository = RecordingRepository()
    with TestClient(
        create_app(lambda: graph, api_key="test-secret", repository=repository)
    ) as client:
        for index, question in enumerate(
            [
                "Classe les actions de shared",
                "Alpha, mais sur quelle période ?",
                "Finalement Beta, YTD",
            ]
        ):
            response = client.post(
                "/v1/chat",
                headers=AUTH,
                json={"thread_id": "crossed", "question": question},
            )
            assert response.status_code == 200
            if index < 2:
                assert_stopped(
                    response,
                    repository.runs[index],
                    "needs_clarification",
                    "refinement" if index else "understanding",
                )
                assert response.json()["validation"]["issue_codes"] == [
                    "ambiguous_universe" if index == 0 else "clarify_period"
                ]
                assert provider.calls == []
            else:
                assert response.json()["status"] == "success"
                assert len(provider.calls) == 2
    assert all("previous_request" in json.loads(call["input"]) for call in calls[1:])
