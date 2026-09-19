from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=4000)
    thread_id: str | None = Field(default=None, min_length=1, max_length=128)
    include_evidence: bool = True

    @field_validator("question")
    @classmethod
    def reject_blank_question(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must contain non-whitespace text")
        return value

    @field_validator("thread_id")
    @classmethod
    def reject_blank_thread_id(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("thread_id must contain non-whitespace text")
        return value


class AnalysisRequestSnapshot(BaseModel):
    objective: str
    metrics: list[str]
    assets: list[str]
    universe: str | None
    start_date: str | None
    end_date: str | None
    target_date: str | None
    market_period: str | None
    benchmark: str | None
    constraints: list[str]
    ranking_direction: str | None
    top_n: int | None
    performance_measure: str
    horizons: list[str]
    user_context: str | None
    unresolved: list[str]


class ValidationSnapshot(BaseModel):
    status: Literal["ready", "needs_clarification", "unsupported"]
    issues: list[str]
    issue_codes: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    request_id: str
    thread_id: str
    status: Literal["success", "needs_clarification", "unsupported"]
    answer: str
    request: AnalysisRequestSnapshot
    validation: ValidationSnapshot
    evidence: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    request_id: str
    detail: str


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    useful: bool = Field(strict=True)
    comment: str | None = Field(default=None, max_length=2000)


class FeedbackResponse(BaseModel):
    feedback_id: UUID
    request_id: UUID
    status: Literal["stored"] = "stored"
