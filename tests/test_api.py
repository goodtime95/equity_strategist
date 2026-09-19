import asyncio
import json
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from equity_strategist.api import server
from equity_strategist.api.body_limit import MAX_CHAT_BODY_BYTES
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


@pytest.mark.parametrize(
    ("configured", "expected"),
    [("configured-model", "configured-model"), ("", "gpt-5.6"), ("  ", "gpt-5.6")],
)
def test_model_setting_is_passed_to_pipeline(monkeypatch, configured, expected) -> None:
    models = []
    monkeypatch.setenv("EQUITY_STRATEGIST_MODEL", configured)
    monkeypatch.setattr(
        server, "build_llm_equity_strategist", lambda model: models.append(model)
    )
    monkeypatch.setattr(server, "EquityStrategistGraph", lambda strategist: strategist)
    server.build_graph()
    assert models == [expected]


@pytest.mark.parametrize("key", ["", "   ", "non-ascii-é", "space key", "key\n"])
def test_invalid_api_configuration_rejected_at_startup(key) -> None:
    with pytest.raises(RuntimeError, match="EQUITY_STRATEGIST_API_KEY"):
        with TestClient(create_app(FakeGraph, api_key=key)):
            pass


@pytest.mark.parametrize("key", [None, "", "   "])
def test_missing_openai_configuration_rejected_at_startup(monkeypatch, key) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    if key is not None:
        monkeypatch.setenv("OPENAI_API_KEY", key)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        with TestClient(create_app(api_key="test-secret")):
            pass


def test_production_startup_and_health_do_not_construct_runtime(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "configured-secret")

    def unexpected_build():
        pytest.fail("startup must not build the provider runtime")

    monkeypatch.setattr(server, "build_graph", unexpected_build)
    with TestClient(create_app(api_key="test-secret")) as client:
        assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize(
    "authorization", [b"Bearer \xff", b"Bearer", b"Bearer ", b"Basic test-secret"]
)
def test_invalid_bearer_tokens_return_401(authorization) -> None:
    graph = FakeGraph()
    with TestClient(create_app(lambda: graph, api_key="test-secret")) as client:
        response = client.post(
            "/v1/chat",
            headers=[(b"authorization", authorization)],
            json={"question": "test"},
        )
    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}
    assert graph.calls == []


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
        {"question": "x", "unexpected": True},
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


@pytest.mark.parametrize(
    "stage", ["runtime_initialization", "graph_invocation", "response_serialization"]
)
def test_unexpected_failure_is_sanitized(caplog, monkeypatch, stage) -> None:
    payload = "raw-provider-response test-secret openai-secret private-question"
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")

    def fail(*args, **kwargs):
        raise RuntimeError(payload)

    class BrokenGraph:
        def invoke(self, question: str, thread_id: str) -> None:
            fail()

    factory = BrokenGraph
    if stage == "runtime_initialization":
        factory = fail
    elif stage == "response_serialization":
        factory = FakeGraph
        monkeypatch.setattr(server, "serialize_chat_result", fail)
    client = TestClient(create_app(factory, api_key="test-secret"))
    response = client.post(
        "/v1/chat",
        headers={**AUTH, "X-Private-Header": "private-header"},
        json={"question": "private-question", "thread_id": "private-thread"},
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
    UUID(response.json()["request_id"])
    records = [record for record in caplog.records if record.name == server.__name__]
    assert len(records) == 1
    assert json.loads(records[0].getMessage()) == {
        "event": "chat_failed",
        "request_id": response.json()["request_id"],
        "stage": stage,
        "error_category": "internal_error",
    }
    assert records[0].exc_info is None
    for sensitive in (*payload.split(), "private-header", "private-thread"):
        assert sensitive not in caplog.text
        assert sensitive not in response.text


@pytest.mark.parametrize("path", ["/v1/chat", "/v1/chat/"])
def test_oversized_body_with_content_length_returns_413(path) -> None:
    graph = FakeGraph()
    client = TestClient(create_app(lambda: graph, api_key="test-secret"))
    response = client.post(path, headers=AUTH, content=b" " * (MAX_CHAT_BODY_BYTES + 1))
    assert response.status_code == 413
    assert response.json() == {"detail": "Request body too large"}
    assert graph.calls == []


@pytest.mark.parametrize("content_length", [None, b"1"])
@pytest.mark.parametrize("extra_bytes", [0, 1])
def test_streamed_body_limit_counts_actual_bytes(content_length, extra_bytes) -> None:
    # Call ASGI directly: TestClient may coalesce a streaming iterable into one
    # message. Exercise separate receive messages and a lying/missing length.
    graph = FakeGraph()
    app = create_app(lambda: graph, api_key="test-secret")
    prefix = b'{"question":"price"}'
    chunks = [prefix, b" " * (MAX_CHAT_BODY_BYTES - len(prefix)), b" " * extra_bytes]
    headers = [
        (b"authorization", b"Bearer test-secret"),
        (b"content-type", b"application/json"),
    ]
    if content_length is not None:
        headers.append((b"content-length", content_length))
    messages = []

    async def run():
        async def receive():
            chunk = chunks.pop(0)
            return {"type": "http.request", "body": chunk, "more_body": bool(chunks)}

        async def send(message):
            messages.append(message)

        await app(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": "/v1/chat",
                "query_string": b"",
                "headers": headers,
                "server": ("testserver", 80),
                "client": ("testclient", 123),
                "root_path": "",
            },
            receive,
            send,
        )

    asyncio.run(run())
    assert messages[0]["status"] == (413 if extra_bytes else 200)
    assert len(graph.calls) == (0 if extra_bytes else 1)
