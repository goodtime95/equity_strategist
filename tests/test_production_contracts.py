import json
from datetime import date
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from equity_strategist.api.server import create_app
from equity_strategist.application.telemetry import (
    observing,
    report_progress,
    stage_timing,
)
from equity_strategist.domain.analysis_plan import AnalysisPlan, Capability, PlanStep
from equity_strategist.domain.analysis_request import (
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
)
from equity_strategist.domain.errors import InsufficientDataError, ProviderFailure
from equity_strategist.persistence.settings import PersistenceSettings
from equity_strategist.tools.exceptions import AmbiguousAssetError, AssetNotFoundError
from tests.test_api import AUTH, FakeGraph
from tests.test_equity_executor import build_executor
from tests.test_run_telemetry import RecordingRepository


@pytest.mark.parametrize("useful", [True, False, 1, 0])
@pytest.mark.parametrize("comment", [None, "", "Useful detail"])
@pytest.mark.parametrize("full", [False, True])
def test_feedback_shortcut_roundtrip(useful, comment, full):
    repository = RecordingRepository()
    with TestClient(
        create_app(
            FakeGraph,
            api_key="test-secret",
            repository=repository,
            persistence_settings=PersistenceSettings(persist_content=full),
        )
    ) as client:
        run = client.post("/v1/chat", headers=AUTH, json={"question": "test"})
        request_id = run.json()["request_id"]
        response = client.post(
            "/v1/feedback",
            headers=AUTH,
            json={
                "request_id": request_id,
                "useful": useful,
                "comment": comment,
            },
        )
    assert response.status_code == 201
    assert response.json()["request_id"] == request_id
    assert repository.feedback[0].request_id == repository.runs[0].request_id
    assert repository.feedback[0].useful is bool(useful)
    assert repository.feedback[0].comment == (comment if full else None)


@pytest.mark.parametrize("value", [2, -1, 1.0, 0.0, "1", "0", "true", "yes", None])
def test_feedback_rejects_other_coercions(value):
    with TestClient(create_app(FakeGraph, api_key="test-secret")) as client:
        response = client.post(
            "/v1/feedback",
            headers=AUTH,
            json={
                "request_id": str(uuid4()),
                "useful": value,
            },
        )
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("error_type", "status", "category"),
    [
        (InsufficientDataError, 422, "insufficient_data"),
        (AmbiguousAssetError, 422, "ambiguous_asset"),
        (AssetNotFoundError, 422, "asset_not_found"),
        (ProviderFailure, 502, "provider_failure"),
    ],
)
def test_typed_failure_is_not_internal_error(error_type, status, category):
    class BrokenGraph:
        def invoke(self, question, thread_id):
            with stage_timing("execution"):
                raise error_type("private provider payload")

    repository = RecordingRepository()
    with TestClient(
        create_app(
            BrokenGraph,
            api_key="test-secret",
            repository=repository,
        )
    ) as client:
        response = client.post("/v1/chat", headers=AUTH, json={"question": "test"})
    assert response.status_code == status
    assert response.json()["error_category"] == category
    assert repository.runs[0].error_category == category
    assert str(repository.runs[0].request_id) == response.json()["request_id"]
    assert "private" not in response.text
    assert "traceback" not in response.text


def test_failure_diagnostic_has_safe_stack_and_step(caplog):
    class BrokenGraph:
        def invoke(self, question, thread_id):
            with stage_timing("execution"):
                report_progress("execution_step", "compare_performance")
                raise RuntimeError("private provider payload test-secret")

    with TestClient(create_app(BrokenGraph, api_key="test-secret")) as client:
        response = client.post("/v1/chat", headers=AUTH, json={"question": "test"})
    records = [r for r in caplog.records if r.name.endswith("run_coordinator")]
    diagnostic = json.loads(records[0].getMessage())
    assert diagnostic["request_id"] == response.json()["request_id"]
    UUID(diagnostic["request_id"])
    assert diagnostic["stage"] == "execution"
    assert diagnostic["step"] == "compare_performance"
    assert diagnostic["exception_type"] == "RuntimeError"
    assert diagnostic["message"]
    assert diagnostic["traceback"][-1]["function"] == "invoke"
    assert diagnostic["traceback"][-1]["line"] > 0
    assert "private provider payload" not in caplog.text
    assert "test-secret" not in caplog.text


@pytest.mark.parametrize("shared_failure", [False, True])
def test_real_executor_reports_failing_operation(monkeypatch, shared_failure):
    executor = build_executor()
    request = AnalysisRequest(
        objective=AnalysisObjective.COMPARE,
        metrics=(AnalysisMetric.PERFORMANCE,),
        assets=("LVMH", "Safran"),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )
    plan = AnalysisPlan(request, (PlanStep(Capability.COMPARE_PERFORMANCE),))

    def fail(*args, **kwargs):
        raise RuntimeError("failure")

    if shared_failure:
        monkeypatch.setattr(executor, "_build_shared_dataset", fail)
    else:
        monkeypatch.setattr(executor.performance_analysis_service, "compare", fail)
    progress = {}
    with observing(None, progress.__setitem__), pytest.raises(RuntimeError):
        executor.execute(plan)
    assert progress["execution_step"] == (
        "shared_dataset" if shared_failure else "compare_performance"
    )
