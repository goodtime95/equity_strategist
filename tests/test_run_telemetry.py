from dataclasses import asdict
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from equity_strategist.api.serialization import serialize_chat_result
from equity_strategist.application import run_coordinator
from equity_strategist.application.run_coordinator import AnalysisRunCoordinator
from equity_strategist.application.run_snapshot import error_category
from equity_strategist.application.telemetry import observing, stage_timing
from equity_strategist.application.thread_identity import persistent_thread_id
from equity_strategist.domain.errors import InsufficientDataError, ProviderFailure
from equity_strategist.domain.request_validation import RequestStatus
from equity_strategist.interpretation.llm import LLMInterpretation
from equity_strategist.strategists.graph import EquityStrategistGraph
from equity_strategist.strategists.graph_state import validation_from_state
from equity_strategist.strategists.validator import AnalysisRequestValidator
from equity_strategist.tools.exceptions import AmbiguousAssetError, AssetNotFoundError
from tests.test_api import FakeGraph
from tests.test_equity_graph import FakeStrategist


class RecordingRepository:
    def __init__(self):
        self.runs = []
        self.feedback = []

    def save_run(self, snapshot):
        self.runs.append(snapshot)

    def save_feedback(self, item):
        self.feedback.append(item)

    def close(self):
        pass


def invoke(coordinator, graph=None, include_evidence=False):
    graph = graph or FakeGraph()
    return coordinator.run(
        "private question",
        "pilot-thread",
        lambda: graph.invoke("private question", "pilot-thread"),
        lambda result, request_id: serialize_chat_result(
            result, request_id, "pilot-thread", include_evidence
        ),
    )


@pytest.mark.parametrize("full", [False, True])
def test_content_policy_and_independent_evidence(full):
    repository = RecordingRepository()
    run = invoke(AnalysisRunCoordinator(repository, persist_content=full))
    assert not run.failed
    assert run.response.evidence is None
    snapshot = repository.runs[0]
    assert str(snapshot.request_id) == run.response.request_id
    assert snapshot.thread_id == persistent_thread_id("pilot-thread")
    assert snapshot.created_at.tzinfo == UTC
    assert snapshot.created_at <= snapshot.completed_at <= datetime.now(UTC)
    assert snapshot.duration_ms >= 0
    assert snapshot.outcome_status == "success"
    assert snapshot.snapshot_version == 1
    if full:
        assert snapshot.question == "private question"
        assert snapshot.request_json["assets"] == ["LVMH"]
        assert snapshot.evidence_json["steps"][0]["result"]["price"] == "99.50"
        assert snapshot.answer == "fake answer"
        assert snapshot.content_mode == "full"
    else:
        for field in ("question", "request_json", "evidence_json", "answer"):
            assert getattr(snapshot, field) is None
        assert "private question" not in str(asdict(snapshot))
        assert snapshot.content_mode == "metadata_only"


def test_storage_and_snapshot_failures_do_not_suppress_success(monkeypatch, caplog):
    class BrokenRepository:
        def save_run(self, snapshot):
            raise RuntimeError("Bearer secret DATABASE_URL private raw data")

    assert not invoke(AnalysisRunCoordinator(BrokenRepository())).failed

    def broken_snapshot(**kwargs):
        raise RuntimeError("secret snapshot failure")

    monkeypatch.setattr(run_coordinator, "build_snapshot", broken_snapshot)
    assert not invoke(AnalysisRunCoordinator()).failed
    assert "secret" not in caplog.text
    assert "private" not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def test_graph_timings_and_observer_failure_do_not_change_result():
    graph = EquityStrategistGraph(FakeStrategist())
    observations = []
    with observing(observations.append):
        result = graph.invoke("question", "observed")
    assert [item.stage for item in observations] == [
        "understanding",
        "validation",
        "planning",
        "execution",
        "interpretation",
    ]
    assert all(item.duration_ms >= 0 and not item.failed for item in observations)

    def broken(*args):
        raise RuntimeError("observer failed")

    with observing(broken, broken):
        actual = graph.invoke("question", "broken-observer")
    assert actual == result
    assert (
        "telemetry"
        not in graph.graph.get_state({"configurable": {"thread_id": "observed"}}).values
    )


def test_fallback_is_observed_separately():
    def fail(**kwargs):
        raise RuntimeError("private provider data")

    interpretation = LLMInterpretation(
        client=SimpleNamespace(responses=SimpleNamespace(create=fail))
    )
    execution = FakeGraph().invoke("question", "thread")["execution"]
    observations = []
    with observing(observations.append):
        answer = interpretation.interpret(execution)
    assert answer
    assert [item.stage for item in observations] == ["interpretation_fallback"]


def test_failed_execution_preserves_completed_intent_and_plan():
    repository = RecordingRepository()
    strategist = FakeStrategist()

    def fail(plan):
        raise InsufficientDataError("secret raw provider details")

    strategist.executor.execute = fail
    graph = EquityStrategistGraph(strategist)
    response = invoke(AnalysisRunCoordinator(repository, persist_content=True), graph)
    assert response.failed
    snapshot = repository.runs[0]
    assert snapshot.outcome_status == "insufficient_data"
    assert snapshot.request_json["objective"] == "compare"
    assert snapshot.planned_capabilities
    assert snapshot.error_metadata == {"stage": "execution"}
    assert snapshot.evidence_json is None
    assert "secret" not in str(asdict(snapshot))
    assert snapshot.telemetry_json["stages"][-1]["failed"] is True


@pytest.mark.parametrize(
    ("exception", "expected"),
    [
        (ProviderFailure("private"), "provider_failure"),
        (InsufficientDataError("private"), "insufficient_data"),
        (AmbiguousAssetError("private"), "ambiguous_asset"),
        (AssetNotFoundError("private"), "asset_not_found"),
        (ValueError("No price observations available"), "internal_error"),
    ],
)
def test_error_categories_are_typed_not_inferred_from_prose(exception, expected):
    assert error_category(exception) == expected


def test_full_content_redacts_known_secrets(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "a-private-api-key")
    repository = RecordingRepository()
    coordinator = AnalysisRunCoordinator(repository, persist_content=True)
    coordinator.run(
        "a-private-api-key Bearer private-token postgresql://user:password@db/name",
        "thread",
        lambda: FakeGraph().invoke("test", "thread"),
        lambda result, request_id: result["answer"],
    )
    content = str(asdict(repository.runs[0]))
    for secret in ("a-private-api-key", "private-token", "password"):
        assert secret not in content


def test_validation_codes_and_old_checkpoint_compatibility():
    from equity_strategist.domain.analysis_request import (
        AnalysisObjective,
        AnalysisRequest,
    )

    request = AnalysisRequest(objective=AnalysisObjective.GET, metrics=())
    validation = AnalysisRequestValidator().validate(request)
    assert validation.issue_codes == ("missing_asset_source", "missing_metric")
    restored = validation_from_state({"status": "needs_clarification", "issues": ["x"]})
    assert restored.issue_codes == ()


@pytest.mark.parametrize(
    "status", [RequestStatus.NEEDS_CLARIFICATION, RequestStatus.UNSUPPORTED]
)
def test_non_success_validation_is_persisted(status):
    repository = RecordingRepository()
    response = invoke(AnalysisRunCoordinator(repository), FakeGraph(status))
    assert not response.failed
    assert repository.runs[0].outcome_status == status.value
    assert repository.runs[0].evidence_json is None


def test_context_is_reset_after_exception():
    observations = []
    with pytest.raises(ValueError), observing(observations.append):
        with stage_timing("execution"):
            raise ValueError("x")
    with stage_timing("execution"):
        pass
    assert len(observations) == 1
    assert observations[0].failed


def test_request_ids_are_unique_per_turn():
    repository = RecordingRepository()
    coordinator = AnalysisRunCoordinator(repository)
    invoke(coordinator)
    invoke(coordinator)
    assert repository.runs[0].request_id != repository.runs[1].request_id
    assert isinstance(repository.runs[0].request_id, UUID)
    assert repository.runs[0].thread_id == repository.runs[1].thread_id


def test_refinement_timing_and_turn_isolation():
    from tests.test_equity_graph import FakeConversationStrategist

    repository = RecordingRepository()
    coordinator = AnalysisRunCoordinator(repository)
    graph = EquityStrategistGraph(FakeConversationStrategist())
    invoke(coordinator, graph)
    coordinator.run(
        "Volatility",
        "pilot-thread",
        lambda: graph.invoke("Volatility", "pilot-thread"),
        lambda result, request_id: result["answer"],
    )
    first, second = repository.runs
    assert first.outcome_status == "needs_clarification"
    assert first.planned_capabilities == []
    assert second.outcome_status == "success"
    assert first.telemetry_json["stages"][0]["stage"] == "understanding"
    assert second.telemetry_json["stages"][0]["stage"] == "refinement"
    assert first.request_id != second.request_id


def test_serializer_failure_keeps_deterministic_evidence():
    repository = RecordingRepository()

    def fail(result, request_id):
        raise RuntimeError("private serialization detail")

    run = AnalysisRunCoordinator(repository, persist_content=True).run(
        "question",
        "thread",
        lambda: FakeGraph().invoke("q", "t"),
        fail,
    )
    assert run.failed
    assert repository.runs[0].error_category == "internal_error"
    assert repository.runs[0].error_metadata == {"stage": "response_serialization"}
    assert repository.runs[0].evidence_json["steps"]


def test_provider_error_boundary_preserves_unknown_errors(monkeypatch):
    from yfinance.exceptions import YFRateLimitError

    import equity_strategist.data_providers.yahoo as yahoo
    from equity_strategist.data_providers.yahoo import YahooFinanceProvider

    def rate_limited(*args, **kwargs):
        raise YFRateLimitError()

    monkeypatch.setattr(yahoo.yf, "Search", rate_limited)
    with pytest.raises(ProviderFailure):
        YahooFinanceProvider().search_assets("example")

    def unknown(*args, **kwargs):
        raise ValueError("private")

    monkeypatch.setattr(yahoo.yf, "Search", unknown)
    with pytest.raises(ValueError):
        YahooFinanceProvider().search_assets("example")


def test_understanding_client_failure_is_typed():
    import httpx
    from openai import APIConnectionError

    from equity_strategist.understanding.llm import LLMUnderstanding

    def fail(**kwargs):
        raise APIConnectionError(request=httpx.Request("POST", "https://example.com"))

    understanding = LLMUnderstanding(
        client=SimpleNamespace(responses=SimpleNamespace(create=fail))
    )
    with pytest.raises(ProviderFailure):
        understanding.understand("question")


def test_timing_clock_failure_does_not_change_graph_behavior(monkeypatch):
    from equity_strategist.application import telemetry

    def broken_clock():
        raise RuntimeError("clock failed")

    monkeypatch.setattr(telemetry, "perf_counter", broken_clock)
    observations = []
    with observing(observations.append):
        result = EquityStrategistGraph(FakeStrategist()).invoke("question")
    assert result["answer"] == "fake answer"
    assert observations == []


def test_broken_logging_sink_does_not_suppress_success(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("sink unavailable")

    monkeypatch.setattr(run_coordinator, "build_snapshot", fail)
    monkeypatch.setattr(run_coordinator.LOGGER, "warning", fail)
    result = invoke(AnalysisRunCoordinator())
    assert not result.failed
    assert result.response.answer == "fake answer"
