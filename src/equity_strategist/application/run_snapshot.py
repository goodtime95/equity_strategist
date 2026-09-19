"""Explicit storage contract; never serialize graph state or arbitrary objects."""

import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from equity_strategist.application.thread_identity import persistent_thread_id
from equity_strategist.domain.errors import (
    ErrorCategory,
    InsufficientDataError,
    ProviderFailure,
)
from equity_strategist.interpretation.evidence import serialize_execution_evidence
from equity_strategist.strategists.graph_state import (
    EquityGraphResult,
    analysis_request_to_state,
)
from equity_strategist.tools.exceptions import AmbiguousAssetError, AssetNotFoundError


@dataclass(frozen=True)
class RunSnapshot:
    request_id: UUID
    thread_id: str
    created_at: datetime
    completed_at: datetime
    duration_ms: float
    outcome_status: str
    validation_status: str | None
    question: str | None
    request_json: dict | None
    validation_issue_codes: list[str]
    planned_capabilities: list[str]
    evidence_json: dict | None
    answer: str | None
    error_category: str | None
    error_metadata: dict[str, str]
    telemetry_json: dict
    model_metadata: dict[str, str]
    app_version: str | None
    git_version: str | None
    snapshot_version: int = 1
    content_mode: str = "metadata_only"


def error_category(error: Exception | None) -> str | None:
    if error is None:
        return None
    for cls, category in (
        (ProviderFailure, ErrorCategory.PROVIDER_FAILURE),
        (InsufficientDataError, ErrorCategory.INSUFFICIENT_DATA),
        (AmbiguousAssetError, ErrorCategory.AMBIGUOUS_ASSET),
        (AssetNotFoundError, ErrorCategory.ASSET_NOT_FOUND),
    ):
        if isinstance(error, cls):
            return category.value
    return ErrorCategory.INTERNAL_ERROR.value


def redact_content(value: Any, secret_values: tuple[str, ...] = ()) -> Any:
    """Defense in depth for content fields, not a generic object serializer.

    Only explicitly selected strings/dicts/lists reach this function. Prompts,
    provider payloads, headers and environment mappings are never inputs.
    """
    if isinstance(value, str):
        secrets = secret_values + tuple(
            os.getenv(name, "")
            for name in ("OPENAI_API_KEY", "EQUITY_STRATEGIST_API_KEY", "DATABASE_URL")
        )
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[REDACTED]")
        value = re.sub(r"(?i)bearer\s+[^\s,;]+", "Bearer [REDACTED]", value)
        value = re.sub(r"\bsk-[A-Za-z0-9_-]+", "[REDACTED]", value)
        value = re.sub(r"postgres(?:ql)?(?:\+psycopg)?://[^\s]+", "[REDACTED]", value)
        return value
    if isinstance(value, dict):
        return {key: redact_content(item, secret_values) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_content(item, secret_values) for item in value]
    return value


def build_snapshot(
    *,
    request_id: UUID,
    thread_id: str,
    created_at: datetime,
    completed_at: datetime,
    duration_ms: float,
    question: str,
    result: EquityGraphResult | None,
    error: Exception | None,
    failure_stage: str | None,
    telemetry: dict,
    persist_content: bool,
    model_metadata: dict[str, str],
    app_version: str | None,
    git_version: str | None,
    secret_values: tuple[str, ...] = (),
) -> RunSnapshot:
    def safe_content(value: Any) -> Any:
        return redact_content(value, secret_values)

    result = result or {}
    validation = result.get("validation")
    validation_status = validation.status.value if validation else None
    category = error_category(error)
    outcome = (
        category
        or ("success" if validation_status == "ready" else validation_status)
        or "internal_error"
    )
    ready = validation_status == "ready"
    request = result.get("request")
    plan = result.get("plan")
    return RunSnapshot(
        request_id=request_id,
        thread_id=persistent_thread_id(thread_id),
        created_at=created_at,
        completed_at=completed_at,
        duration_ms=max(0, duration_ms),
        outcome_status=outcome,
        validation_status=validation_status,
        question=safe_content(question) if persist_content else None,
        request_json=safe_content(dict(analysis_request_to_state(request)))
        if persist_content and request
        else None,
        validation_issue_codes=list(validation.issue_codes) if validation else [],
        planned_capabilities=[step.capability.value for step in plan.steps]
        if ready and plan
        else [],
        evidence_json=safe_content(serialize_execution_evidence(result["execution"]))
        if persist_content and ready and "execution" in result
        else None,
        answer=safe_content(result.get("answer")) if persist_content else None,
        error_category=category,
        error_metadata={"stage": failure_stage} if category and failure_stage else {},
        telemetry_json=telemetry,
        model_metadata=safe_content(model_metadata),
        app_version=safe_content(app_version),
        git_version=safe_content(git_version),
        content_mode="full" if persist_content else "metadata_only",
    )
