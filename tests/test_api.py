from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from equity_strategist.api import server
from equity_strategist.api.server import create_app
from equity_strategist.domain.analysis_execution import (
    AnalysisExecutionResult,
    StepExecutionResult,
)
from equity_strategist.domain.analysis_plan import AnalysisPlan, Capability, PlanStep
from equity_strategist.domain.analysis_request import (
    AnalysisMetric,
    AnalysisObjective,
    AnalysisRequest,
)
from equity_strategist.domain.asset import Asset
from equity_strategist.domain.request_validation import (
    RequestStatus,
    RequestValidationResult,
)
from equity_strategist.domain.results import PriceOnDateResult

AUTH = {"Authorization": "Bearer test-secret"}


class FakeGraph:
    def __init__(self, status: RequestStatus = RequestStatus.READY) -> None:
        self.status = status
        self.calls: list[tuple[str, str]] = []

    def invoke(self, question: str, thread_id: str) -> dict:
        self.calls.append((question, thread_id))
        request = AnalysisRequest(
            objective=AnalysisObjective.GET,
            metrics=(AnalysisMetric.PRICE,),
            assets=("LVMH",),
            target_date=date(2025, 12, 31),
        )
        result = {
            "request": request,
            "validation": RequestValidationResult(self.status, ("issue",)),
            "answer": "fake answer",
        }
        if self.status == RequestStatus.READY:
            plan = AnalysisPlan(request, (PlanStep(Capability.PRICE_ON_DATE),))
            price = PriceOnDateResult(
                Asset("MC.PA", "LVMH", currency="EUR"),
                date(2025, 12, 31),
                date(2025, 12, 30),
                Decimal("99.50"),
                "adjusted_close",
                True,
            )
            result["execution"] = AnalysisExecutionResult(
                plan, (StepExecutionResult(Capability.PRICE_ON_DATE, price),)
            )
        return result


def test_health_is_public_and_does_not_build_runtime() -> None:
    builds = []
    client = TestClient(create_app(lambda: builds.append(1), api_key="test-secret"))
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    assert builds == []


def test_missing_api_key_prevents_server_startup(monkeypatch) -> None:
    monkeypatch.delenv("EQUITY_STRATEGIST_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="EQUITY_STRATEGIST_API_KEY"):
        with TestClient(create_app(lambda: FakeGraph())):
            pass


def test_model_setting_is_passed_to_pipeline(monkeypatch) -> None:
    models = []
    monkeypatch.setenv("EQUITY_STRATEGIST_MODEL", "configured-model")
    monkeypatch.setattr(
        server, "build_llm_equity_strategist", lambda model: models.append(model)
    )
    monkeypatch.setattr(server, "EquityStrategistGraph", lambda strategist: strategist)
    server.build_graph()
    assert models == ["configured-model"]


def test_auth_and_body_validation() -> None:
    client = TestClient(create_app(lambda: FakeGraph(), api_key="test-secret"))
    assert client.post("/v1/chat", json={"question": "test"}).status_code == 401
    assert (
        client.post(
            "/v1/chat",
            headers={"Authorization": "Bearer wrong"},
            json={"question": "test"},
        ).status_code
        == 401
    )
    for body in (
        {"question": ""},
        {"question": "   "},
        {"question": "x" * 4001},
        {"question": "x", "thread_id": ""},
    ):
        assert client.post("/v1/chat", headers=AUTH, json=body).status_code == 422


def test_success_mapping_thread_ids_evidence_and_runtime_reuse() -> None:
    graph = FakeGraph()
    builds = []

    def factory() -> FakeGraph:
        builds.append(1)
        return graph

    client = TestClient(create_app(factory, api_key="test-secret"))
    first = client.post("/v1/chat", headers=AUTH, json={"question": "price"})
    assert first.status_code == 200
    payload = first.json()
    UUID(payload["request_id"])
    UUID(payload["thread_id"])
    assert payload["status"] == "success"
    assert payload["validation"]["status"] == "ready"
    assert payload["request"]["target_date"] == "2025-12-31"
    assert payload["evidence"]["steps"][0]["result"]["price"] == "99.50"
    assert "plan" not in payload

    second = client.post(
        "/v1/chat",
        headers=AUTH,
        json={
            "question": "more",
            "thread_id": payload["thread_id"],
            "include_evidence": False,
        },
    )
    assert second.json()["thread_id"] == payload["thread_id"]
    assert second.json()["evidence"] is None
    assert graph.calls[1] == ("more", payload["thread_id"])
    assert builds == [1]


def test_supplied_thread_and_domain_outcomes() -> None:
    for status in (RequestStatus.NEEDS_CLARIFICATION, RequestStatus.UNSUPPORTED):
        graph = FakeGraph(status)
        client = TestClient(
            create_app(lambda graph=graph: graph, api_key="test-secret")
        )
        response = client.post(
            "/v1/chat",
            headers=AUTH,
            json={"question": "test", "thread_id": "existing-thread"},
        )
        assert response.status_code == 200
        assert response.json()["thread_id"] == "existing-thread"
        assert response.json()["status"] == status.value
        assert response.json()["validation"]["issues"] == ["issue"]
        assert response.json()["evidence"] is None


def test_unexpected_failure_is_sanitized(caplog) -> None:
    class BrokenGraph:
        def invoke(self, question: str, thread_id: str) -> None:
            raise RuntimeError("provider failure test-secret")

    client = TestClient(create_app(BrokenGraph, api_key="test-secret"))
    response = client.post("/v1/chat", headers=AUTH, json={"question": "test"})
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
    UUID(response.json()["request_id"])
    assert "provider failure" not in response.text
    assert "test-secret" not in caplog.text
    assert "[REDACTED]" in caplog.text
