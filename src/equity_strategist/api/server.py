import logging
import os
import secrets
import threading
import traceback
from collections.abc import Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse

from equity_strategist.api.schemas import ChatRequest, ChatResponse
from equity_strategist.api.serialization import serialize_chat_result
from equity_strategist.app import build_llm_equity_strategist
from equity_strategist.strategists.graph import EquityStrategistGraph

LOGGER = logging.getLogger(__name__)


def build_graph() -> EquityStrategistGraph:
    model = os.getenv("EQUITY_STRATEGIST_MODEL", "gpt-5.6")
    return EquityStrategistGraph(build_llm_equity_strategist(model=model))


def create_app(
    graph_factory: Callable[[], EquityStrategistGraph] = build_graph,
    api_key: str | None = None,
) -> FastAPI:
    """Create one graph runtime and API-key configuration per server process."""
    configured_key = (
        api_key if api_key is not None else os.getenv("EQUITY_STRATEGIST_API_KEY")
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if not configured_key:
            raise RuntimeError("EQUITY_STRATEGIST_API_KEY is required")
        yield

    app = FastAPI(
        title="Equity Strategist API",
        version="1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    runtime_lock = threading.Lock()
    graph: EquityStrategistGraph | None = None

    def require_auth(authorization: str | None = Header(default=None)) -> None:
        if not configured_key:
            raise HTTPException(status_code=503, detail="API key is not configured")
        scheme, _, token = (authorization or "").partition(" ")
        if scheme.lower() != "bearer" or not secrets.compare_digest(
            token, configured_key
        ):
            raise HTTPException(status_code=401, detail="Unauthorized")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/v1/chat", response_model=ChatResponse, dependencies=[Depends(require_auth)]
    )
    def chat(body: ChatRequest) -> ChatResponse | JSONResponse:
        nonlocal graph
        request_id = str(uuid4())
        thread_id = body.thread_id or str(uuid4())
        try:
            # Serial access also protects a single thread's in-memory checkpoint.
            with runtime_lock:
                if graph is None:
                    graph = graph_factory()
                result = graph.invoke(body.question, thread_id=thread_id)
            return serialize_chat_result(
                result, request_id, thread_id, body.include_evidence
            )
        except Exception:
            failure = traceback.format_exc()
            for secret in (configured_key, os.getenv("OPENAI_API_KEY")):
                if secret:
                    failure = failure.replace(secret, "[REDACTED]")
            LOGGER.error("Chat request %s failed:\n%s", request_id, failure)
            return JSONResponse(
                status_code=500,
                content={"request_id": request_id, "detail": "Internal server error"},
            )

    return app


app = create_app()
