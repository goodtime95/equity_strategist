import json
import logging
import os
import secrets
import threading
from collections.abc import Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse

from equity_strategist.api.body_limit import ChatBodyLimitMiddleware
from equity_strategist.api.schemas import ChatRequest, ChatResponse
from equity_strategist.api.serialization import serialize_chat_result
from equity_strategist.app import build_llm_equity_strategist
from equity_strategist.strategists.graph import EquityStrategistGraph

LOGGER = logging.getLogger(__name__)
DEFAULT_MODEL = "gpt-5.6"


def build_graph() -> EquityStrategistGraph:
    model = os.getenv("EQUITY_STRATEGIST_MODEL", "").strip() or DEFAULT_MODEL
    return EquityStrategistGraph(build_llm_equity_strategist(model=model))


def create_app(
    graph_factory: Callable[[], EquityStrategistGraph] | None = None,
    api_key: str | None = None,
) -> FastAPI:
    """Create one graph runtime and API-key configuration per server process."""
    configured_key = (
        api_key if api_key is not None else os.getenv("EQUITY_STRATEGIST_API_KEY")
    )
    runtime_factory = graph_factory or build_graph

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if not configured_key or not configured_key.strip():
            raise RuntimeError("EQUITY_STRATEGIST_API_KEY is required")
        if not all(33 <= ord(character) <= 126 for character in configured_key):
            raise RuntimeError(
                "EQUITY_STRATEGIST_API_KEY must contain visible ASCII without spaces"
            )
        # Injected runtimes may use no OpenAI client. Validate the production
        # runtime's environment without constructing it or contacting providers.
        if graph_factory is None and not os.getenv("OPENAI_API_KEY", "").strip():
            raise RuntimeError("OPENAI_API_KEY is required")
        yield

    app = FastAPI(
        title="Equity Strategist API",
        version="1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(ChatBodyLimitMiddleware)
    runtime_lock = threading.Lock()
    graph: EquityStrategistGraph | None = None

    def require_auth(authorization: str | None = Header(default=None)) -> None:
        if not configured_key:
            raise HTTPException(status_code=503, detail="API key is not configured")
        scheme, _, token = (authorization or "").partition(" ")
        if (
            scheme.lower() != "bearer"
            or not token.isascii()
            or not configured_key.isascii()
            or not secrets.compare_digest(token, configured_key)
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
        stage = "runtime_initialization"
        try:
            # Serial access also protects a single thread's in-memory checkpoint.
            with runtime_lock:
                if graph is None:
                    graph = runtime_factory()
                stage = "graph_invocation"
                result = graph.invoke(body.question, thread_id=thread_id)
            stage = "response_serialization"
            return serialize_chat_result(
                result, request_id, thread_id, body.include_evidence
            )
        except Exception:
            LOGGER.error(
                "%s",
                json.dumps(
                    {
                        "event": "chat_failed",
                        "request_id": request_id,
                        "stage": stage,
                        "error_category": "internal_error",
                    }
                ),
            )
            return JSONResponse(
                status_code=500,
                content={"request_id": request_id, "detail": "Internal server error"},
            )

    return app


app = create_app()
