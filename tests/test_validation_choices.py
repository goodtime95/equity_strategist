"""Regression matrix for source-dependent limits and scoped ambiguity."""

from dataclasses import replace
from datetime import date

import pytest
from fastapi.testclient import TestClient

from equity_strategist import app as composition
from equity_strategist.asset_registry.defaults import build_default_asset_registry
from equity_strategist.asset_registry.registry import AssetRegistry
from equity_strategist.domain.analysis_request import (
    AmbiguityScope,
    AnalysisHorizon,
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
)
from equity_strategist.domain.asset import Asset
from equity_strategist.domain.universe import Universe, UniverseType
from equity_strategist.interpretation.context import InterpretationContext
from equity_strategist.interpretation.deterministic import DeterministicInterpretation
from equity_strategist.strategists.graph_state import (
    analysis_request_from_state,
    analysis_request_to_state,
)
from equity_strategist.strategists.validator import AnalysisRequestValidator
from equity_strategist.universe_registry.defaults import build_default_universe_registry
from equity_strategist.universe_registry.registry import UniverseRegistry
from tests.test_api import AUTH
from tests.test_production_remediation import BASE_REQUEST, http_run, pipeline


def catalog() -> UniverseRegistry:
    first = Universe(
        name="First",
        universe_type=UniverseType.STATIC,
        asset_queries=("LVMH", "Hermès"),
        aliases=("shared",),
    )
    return UniverseRegistry(
        [
            *build_default_universe_registry().universes,
            first,
            replace(first, name="Second"),
        ]
    )


# Each row states the outcome without assets and with two explicit assets.
# Cross these 16 semantic rows only with source choice and state generation.
SOURCE_CASES = [
    (
        "get_performance",
        "Luxury Europe",
        "universe_capability_unsupported",
        "conflicting_asset_sources",
    ),
    (
        "get_performance",
        "eurostoxx 50",
        "universe_capability_unsupported",
        "conflicting_asset_sources",
    ),
    (
        "get_performance",
        "shared",
        "universe_capability_unsupported",
        "conflicting_asset_sources",
    ),
    (
        "get_performance",
        "Private basket X",
        "universe_capability_unsupported",
        "conflicting_asset_sources",
    ),
    (
        "rank_performance",
        "Luxury Europe",
        "unresolved_semantics",
        "conflicting_asset_sources",
    ),
    (
        "rank_performance",
        "eurostoxx 50",
        "universe_unavailable",
        "conflicting_asset_sources",
    ),
    ("rank_performance", "shared", "ambiguous_universe", "conflicting_asset_sources"),
    (
        "rank_performance",
        "Private basket X",
        "universe_unavailable",
        "conflicting_asset_sources",
    ),
    (
        "rank_volatility",
        "Luxury Europe",
        "universe_capability_unsupported",
        "conflicting_asset_sources",
    ),
    (
        "rank_volatility",
        "eurostoxx 50",
        "universe_capability_unsupported",
        "conflicting_asset_sources",
    ),
    (
        "rank_volatility",
        "shared",
        "universe_capability_unsupported",
        "conflicting_asset_sources",
    ),
    (
        "rank_volatility",
        "Private basket X",
        "universe_capability_unsupported",
        "conflicting_asset_sources",
    ),
    (
        "rank_drawdown",
        "Luxury Europe",
        "analysis_combination_unsupported",
        "analysis_combination_unsupported",
    ),
    (
        "rank_drawdown",
        "eurostoxx 50",
        "analysis_combination_unsupported",
        "analysis_combination_unsupported",
    ),
    (
        "rank_drawdown",
        "shared",
        "analysis_combination_unsupported",
        "analysis_combination_unsupported",
    ),
    (
        "rank_drawdown",
        "Private basket X",
        "analysis_combination_unsupported",
        "analysis_combination_unsupported",
    ),
]
CLARIFICATION_CODES = {
    "conflicting_asset_sources",
    "ambiguous_universe",
    "unresolved_semantics",
}


@pytest.mark.parametrize("operation,universe,without_assets,with_assets", SOURCE_CASES)
@pytest.mark.parametrize("explicit_assets", [False, True])
@pytest.mark.parametrize("legacy", [False, True])
def test_source_priority_equivalence_classes(
    operation, universe, without_assets, with_assets, explicit_assets, legacy
):
    objective, metric = operation.split("_")
    request = AnalysisRequest(
        objective=AnalysisObjective(objective),
        metrics=(AnalysisMetric(metric),),
        universe=universe,
        assets=("LVMH", "Hermès") if explicit_assets else (),
        start_date=date(2025, 1, 1),
        end_date=date(2025, 6, 30),
        unresolved=("Meaning requires clarification.",),
        ambiguity_scopes=(AmbiguityScope.UNKNOWN,),
    )
    state = analysis_request_to_state(request)
    if legacy:
        del state["ambiguity_scopes"]
    restored = analysis_request_from_state(state)
    validation = AnalysisRequestValidator(catalog()).validate(restored)
    code = with_assets if explicit_assets else without_assets
    assert code in validation.issue_codes
    assert validation.status.value == (
        "needs_clarification" if code in CLARIFICATION_CODES else "unsupported"
    )
    assert "performance_reference_ambiguous" not in validation.issue_codes
    if code == "conflicting_asset_sources":
        assert "universe_unavailable" not in validation.issue_codes


@pytest.mark.parametrize(
    "universe", ["Luxury Europe", "eurostoxx 50", "shared", "Private basket X"]
)
def test_instrument_reference_equivalence_classes(universe):
    request = replace(
        BASE_REQUEST,
        assets=(),
        universe=universe,
        unresolved=("Which instrument?",),
        ambiguity_scopes=(AmbiguityScope.INSTRUMENT,),
    )
    result = AnalysisRequestValidator(catalog()).validate(request)
    assert result.status.value == "needs_clarification"
    assert result.issue_codes == (
        "performance_reference_ambiguous",
        "unresolved_semantics",
    )


@pytest.mark.parametrize(
    "scope,legacy",
    [(scope, False) for scope in AmbiguityScope] + [(AmbiguityScope.UNKNOWN, True)],
)
def test_unavailable_reference_scopes_through_http(monkeypatch, scope, legacy):
    request = replace(
        BASE_REQUEST,
        assets=(),
        universe="eurostoxx 50",
        unresolved=("Parameter requires clarification.",),
        ambiguity_scopes=(scope,),
    )
    if legacy:
        state = analysis_request_to_state(request)
        del state["ambiguity_scopes"]
        request = analysis_request_from_state(state)
    graph, provider = pipeline(monkeypatch, request)
    response, repository = http_run(graph, "Quelle est la performance YTD ?")
    payload = response.json()
    expected = (
        "needs_clarification"
        if not legacy and scope == AmbiguityScope.INSTRUMENT
        else "unsupported"
    )
    assert response.status_code == 200
    assert payload["status"] == expected
    assert (
        "performance_reference_ambiguous" in payload["validation"]["issue_codes"]
    ) == (expected == "needs_clarification")
    assert ("Quel indice ou instrument" in payload["answer"]) == (
        expected == "needs_clarification"
    )
    assert payload["request"]["horizons"] == ["ytd"]
    assert "ambiguity_scopes" not in payload["request"]  # HTTP DTO unchanged.
    snapshot = repository.runs[0]
    assert snapshot.planned_capabilities == []
    assert not {"planning", "execution"} & {
        s["stage"] for s in snapshot.telemetry_json["stages"]
    }
    assert provider.calls == []


@pytest.mark.parametrize("choose_assets", [True, False])
def test_source_choice_conversation(monkeypatch, choose_assets):
    request = replace(
        BASE_REQUEST,
        objective=AnalysisObjective.RANK,
        assets=("LVMH", "Hermès"),
        universe="eurostoxx 50",
    )
    graph, provider = pipeline(monkeypatch, request)

    def forbidden(*args, **kwargs):
        pytest.fail("Constituent provider must not be called")

    monkeypatch.setattr(
        composition.EuronextUniverseProvider, "get_constituents", forbidden
    )

    class Understanding:
        def understand(self, question):
            return request

        def refine(self, previous_request, clarification):
            assert previous_request == request
            return (
                replace(previous_request, universe=None)
                if choose_assets
                else replace(previous_request, assets=())
            )

    graph.strategist.understanding = Understanding()
    from equity_strategist.api.server import create_app
    from tests.test_run_telemetry import RecordingRepository

    repository = RecordingRepository()
    with TestClient(
        create_app(lambda: graph, api_key="test-secret", repository=repository)
    ) as client:
        first = client.post(
            "/v1/chat",
            headers=AUTH,
            json={
                "question": (
                    "Classe LVMH et Hermès ou les constituants de l’Euro Stoxx 50"
                ),
                "thread_id": "choice",
            },
        )
        assert first.json()["status"] == "needs_clarification"
        assert first.json()["validation"]["issue_codes"] == [
            "conflicting_asset_sources"
        ]
        assert "actifs explicitement nommés" in first.json()["answer"]
        assert "constituants" in first.json()["answer"]
        assert provider.calls == []
        assert repository.runs[0].planned_capabilities == []
        second = client.post(
            "/v1/chat",
            headers=AUTH,
            json={
                "question": "Les actifs" if choose_assets else "L’univers",
                "thread_id": "choice",
                "include_evidence": True,
            },
        )
    payload = second.json()
    assert second.status_code == 200
    assert payload["status"] == ("success" if choose_assets else "unsupported")
    assert payload["request"]["metrics"] == ["performance"]
    assert payload["request"]["horizons"] == ["ytd"]
    if choose_assets:
        assert payload["request"]["assets"] == ["LVMH", "Hermès"]
        assert payload["request"]["universe"] is None
        assert repository.runs[1].planned_capabilities == ["rank_performance"]
        assert len(provider.calls) == 2
    else:
        assert "universe_unavailable" in payload["validation"]["issue_codes"]
        assert repository.runs[1].planned_capabilities == []
        assert provider.calls == []


@pytest.mark.parametrize(
    "metric", [AnalysisMetric.PERFORMANCE, AnalysisMetric.VOLATILITY]
)
def test_shared_alias_only_clarifies_supported_universe_operation(monkeypatch, metric):
    request = replace(
        BASE_REQUEST,
        objective=AnalysisObjective.RANK,
        metrics=(metric,),
        assets=(),
        universe="shared",
        horizons=(),
        start_date=date(2024, 12, 31),
    )
    graph, provider = pipeline(monkeypatch, request)
    shared = catalog()
    graph.strategist.validator.universe_registry = shared
    graph.strategist.executor.universe_constituent_service.universe_registry = shared
    response, repository = http_run(graph, "Classe les actions de cet univers")
    expected = (
        "needs_clarification" if metric == AnalysisMetric.PERFORMANCE else "unsupported"
    )
    assert response.json()["status"] == expected
    assert repository.runs[0].planned_capabilities == []
    assert provider.calls == []
    if metric == AnalysisMetric.PERFORMANCE:
        graph.strategist.understanding.request = replace(request, universe="First")
        resolved, _ = http_run(graph, "Classe les actions du premier univers")
        assert resolved.json()["status"] == "success"
        assert len(provider.calls) == 2
    else:
        assert response.json()["validation"]["issue_codes"] == [
            "universe_capability_unsupported"
        ]
        assert "pas disponible pour un univers" in response.json()["answer"]
        assert "Quel univers" not in response.json()["answer"]


@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize(
    "reference,recognized",
    [
        ("Euro Stoxx 50", True),
        ("SX5E", True),
        ("Private basket X", False),
        ("LVMH", False),
        ("Stoxx", False),
    ],
)
def test_index_suggestion_requires_verified_exact_identity(
    language, reference, recognized
):
    request = replace(
        BASE_REQUEST, objective=AnalysisObjective.RANK, assets=(), universe=reference
    )
    result = AnalysisRequestValidator().validate(request)
    assert result.status.value == "unsupported"
    assert ("index_asset_available" in result.issue_codes) == recognized
    answer = DeterministicInterpretation.interpret_validation(
        result, InterpretationContext(language=language)
    )
    assert (
        "L’indice lui-même" in answer or "locally recognized index" in answer
    ) == recognized
    assert "rank_performance" not in answer and "compare_performance" not in answer


def test_ambiguous_asset_alias_does_not_promise_index():
    index = Asset("verified-index", is_index=True, aliases=("shared",))
    registry = AssetRegistry([index, Asset("stock", aliases=("shared",))])
    validator = AnalysisRequestValidator(asset_registry=registry)
    result = validator.validate(
        replace(
            BASE_REQUEST, objective=AnalysisObjective.RANK, assets=(), universe="shared"
        )
    )
    assert result.issue_codes == ("universe_unavailable",)
    assert registry.known_index("shared") is None
    assert build_default_asset_registry().known_index("SXDP") is None


def test_ambiguity_scope_invariants():
    with pytest.raises(TypeError):
        replace(BASE_REQUEST, unresolved=("unknown",), ambiguity_scopes=("instrument",))
    with pytest.raises(ValueError):
        replace(BASE_REQUEST, ambiguity_scopes=(AmbiguityScope.INSTRUMENT,))


def test_llm_understanding_and_refinement_preserve_structured_scopes():
    import json
    from types import SimpleNamespace

    from equity_strategist.understanding.llm import (
        ANALYSIS_REQUEST_SCHEMA,
        LLMUnderstanding,
    )

    initial = replace(
        BASE_REQUEST,
        assets=(),
        universe="santé",
        unresolved=("Quel indice représente ce secteur ?",),
        ambiguity_scopes=(AmbiguityScope.INSTRUMENT,),
    )
    resolved = replace(
        initial, assets=("S&P 500",), universe=None, unresolved=(), ambiguity_scopes=()
    )
    payloads = iter(
        [analysis_request_to_state(initial), analysis_request_to_state(resolved)]
    )
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(output_text=json.dumps(next(payloads)))

    understanding = LLMUnderstanding(
        client=SimpleNamespace(responses=SimpleNamespace(create=create))
    )
    first = understanding.understand("Performance YTD de la santé ?")
    assert first.ambiguity_scopes == (AmbiguityScope.INSTRUMENT,)
    assert (
        AnalysisRequestValidator().validate(first).status.value == "needs_clarification"
    )
    second = understanding.refine(first, "Finalement le S&P 500")
    assert second.ambiguity_scopes == ()
    assert second.unresolved == ()
    assert second.universe is None and second.assets == ("S&P 500",)
    assert second.horizons == first.horizons == (AnalysisHorizon.YEAR_TO_DATE,)
    assert second.metrics == first.metrics == (AnalysisMetric.PERFORMANCE,)
    previous = json.loads(calls[1]["input"])["previous_request"]
    assert previous["ambiguity_scopes"] == ["instrument"]
    assert previous["horizons"] == ["ytd"]
    assert "ambiguity_scopes" in ANALYSIS_REQUEST_SCHEMA["required"]
    assert set(
        ANALYSIS_REQUEST_SCHEMA["properties"]["ambiguity_scopes"]["items"]["enum"]
    ) == {scope.value for scope in AmbiguityScope}
    assert all("Never infer instrument" in call["instructions"] for call in calls)
    assert AnalysisRequestValidator().validate(second).is_ready


def test_full_snapshot_scopes_roundtrip_and_legacy_default(monkeypatch):
    from equity_strategist.api.serialization import serialize_chat_result
    from equity_strategist.application.run_coordinator import AnalysisRunCoordinator
    from tests.test_run_telemetry import RecordingRepository

    request = replace(
        BASE_REQUEST,
        assets=(),
        universe="santé",
        unresolved=("Which instrument?",),
        ambiguity_scopes=(AmbiguityScope.INSTRUMENT,),
    )
    graph, provider = pipeline(monkeypatch, request)
    repository = RecordingRepository()
    coordinator = AnalysisRunCoordinator(repository, persist_content=True)
    try:
        result = coordinator.run(
            "Performance YTD de la santé ?",
            "snapshot",
            lambda: graph.invoke("Performance YTD de la santé ?", thread_id="snapshot"),
            lambda result, request_id: serialize_chat_result(
                result, request_id, "snapshot", True
            ),
        )
    finally:
        coordinator.close()
    assert not result.failed
    stored = repository.runs[0].request_json
    assert stored["ambiguity_scopes"] == ["instrument"]
    assert (
        analysis_request_from_state(stored).ambiguity_scopes == request.ambiguity_scopes
    )
    old = {key: value for key, value in stored.items() if key != "ambiguity_scopes"}
    legacy = analysis_request_from_state(old)
    assert legacy.ambiguity_scopes == ()
    assert legacy.unresolved == request.unresolved
    assert AnalysisRequestValidator().validate(legacy).status.value == "unsupported"
    assert provider.calls == []
