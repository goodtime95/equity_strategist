import json
import logging
import os
import secrets
import threading
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse

from equity_strategist.api.body_limit import ChatBodyLimitMiddleware
from equity_strategist.api.schemas import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
)
from equity_strategist.api.serialization import serialize_chat_result
from equity_strategist.app import build_llm_equity_strategist
from equity_strategist.application.run_coordinator import AnalysisRunCoordinator
from equity_strategist.application.run_snapshot import redact_content
from equity_strategist.application.telemetry import stage_timing
from equity_strategist.persistence.repository import (
    Feedback,
    NoOpRunRepository,
    RunRepository,
    UnknownRun,
)
from equity_strategist.persistence.settings import PersistenceSettings
from equity_strategist.strategists.graph import EquityStrategistGraph

LOGGER = logging.getLogger(__name__)
DEFAULT_MODEL = "gpt-5.6"


def build_graph() -> EquityStrategistGraph:
    model = os.getenv("EQUITY_STRATEGIST_MODEL", "").strip() or DEFAULT_MODEL
    return EquityStrategistGraph(build_llm_equity_strategist(model=model))


def create_app(
    graph_factory: Callable[[], EquityStrategistGraph] | None = None,
    api_key: str | None = None,
    repository: RunRepository | None = None,
    persistence_settings: PersistenceSettings | None = None,
) -> FastAPI:
    """Create one graph runtime and API-key configuration per server process."""
    configured_key = (
        api_key if api_key is not None else os.getenv("EQUITY_STRATEGIST_API_KEY")
    )
    runtime_factory = graph_factory or build_graph
    try:
        settings = persistence_settings or PersistenceSettings.from_env()
    except Exception:
        LOGGER.warning("persistence_configuration_invalid")
        settings = PersistenceSettings()
    if repository is None:
        repository = NoOpRunRepository()
        if settings.enabled:
            try:
                from equity_strategist.persistence.postgres import (
                    PostgresRunRepository,
                    create_postgres_engine,
                )

                repository = PostgresRunRepository(
                    create_postgres_engine(settings.database_url or "")
                )
            except Exception:
                LOGGER.warning("persistence_initialization_failed")
    coordinator = AnalysisRunCoordinator(
        repository,
        persist_content=settings.persist_content,
        model_metadata={
            "understanding": os.getenv("EQUITY_STRATEGIST_MODEL", "").strip()
            or DEFAULT_MODEL,
            "interpretation": os.getenv("EQUITY_STRATEGIST_MODEL", "").strip()
            or DEFAULT_MODEL,
        }
        if graph_factory is None
        else {},
        git_version=os.getenv("RAILWAY_GIT_COMMIT_SHA"),
        secret_values=(configured_key or "",),
        persistence_timeout_seconds=settings.timeout_seconds,
    )

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
        try:
            yield
        finally:
            try:
                coordinator.close()
            except Exception:
                LOGGER.warning("persistence_close_failed")

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
        thread_id = body.thread_id or str(uuid4())

        def invoke():
            nonlocal graph
            # Serial access protects the graph and in-memory checkpoints.
            with runtime_lock:
                if graph is None:
                    with stage_timing("runtime_initialization"):
                        graph = runtime_factory()
                return graph.invoke(body.question, thread_id=thread_id)

        run = coordinator.run(
            body.question,
            thread_id,
            invoke,
            lambda result, request_id: serialize_chat_result(
                result, request_id, thread_id, body.include_evidence
            ),
        )
        if run.failed:
            LOGGER.error(
                "%s",
                json.dumps(
                    {
                        "event": "chat_failed",
                        "request_id": str(run.request_id),
                        "stage": run.failure_stage,
                        "error_category": run.error_category,
                    }
                ),
            )
            status_code, detail = {
                "insufficient_data": (422, "Insufficient market data"),
                "ambiguous_asset": (422, "Asset identity requires clarification"),
                "asset_not_found": (422, "Asset not found"),
                "provider_failure": (502, "External provider unavailable"),
            }.get(run.error_category, (500, "Internal server error"))
            content = {"request_id": str(run.request_id), "detail": detail}
            if status_code != 500:
                content["error_category"] = run.error_category
            return JSONResponse(status_code=status_code, content=content)
        return run.response

    @app.post(
        "/v1/feedback",
        response_model=FeedbackResponse,
        status_code=201,
        dependencies=[Depends(require_auth)],
    )
    def submit_feedback(body: FeedbackRequest) -> FeedbackResponse:
        item = Feedback(
            feedback_id=uuid4(),
            request_id=body.request_id,
            useful=body.useful,
            comment=(
                redact_content(body.comment, (configured_key or "",))[:2000]
                if settings.persist_content and body.comment is not None
                else None
            ),
            created_at=datetime.now(UTC),
        )
        try:
            repository.save_feedback(item)
        except UnknownRun:
            raise HTTPException(status_code=404, detail="Unknown request") from None
        except Exception:
            raise HTTPException(
                status_code=503, detail="Feedback storage unavailable"
            ) from None
        return FeedbackResponse(
            feedback_id=item.feedback_id, request_id=item.request_id
        )

    return app


app = create_app()
