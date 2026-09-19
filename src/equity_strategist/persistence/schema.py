"""SQLAlchemy Core schema. DDL is executed only by Alembic."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

metadata = sa.MetaData()
analysis_run = sa.Table(
    "analysis_run",
    metadata,
    sa.Column("request_id", UUID(as_uuid=True), primary_key=True),
    sa.Column("thread_id", sa.String(74), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("duration_ms", sa.Double, nullable=False),
    sa.Column("outcome_status", sa.String(32), nullable=False),
    sa.Column("validation_status", sa.String(32)),
    sa.Column("question", sa.Text),
    sa.Column("request_json", JSONB),
    sa.Column("validation_issue_codes", JSONB, nullable=False),
    sa.Column("planned_capabilities", JSONB, nullable=False),
    sa.Column("evidence_json", JSONB),
    sa.Column("answer", sa.Text),
    sa.Column("error_category", sa.String(32)),
    sa.Column("error_metadata", JSONB, nullable=False),
    sa.Column("telemetry_json", JSONB, nullable=False),
    sa.Column("model_metadata", JSONB, nullable=False),
    sa.Column("app_version", sa.String(128)),
    sa.Column("git_version", sa.String(128)),
    sa.Column("snapshot_version", sa.Integer, nullable=False),
    sa.Column("content_mode", sa.String(16), nullable=False),
    sa.CheckConstraint("duration_ms >= 0", name="ck_run_duration"),
    sa.CheckConstraint(
        "thread_id ~ '^thread-v1:[0-9a-f]{64}$'", name="ck_run_thread_identity"
    ),
    sa.CheckConstraint(
        "content_mode IN ('metadata_only', 'full')", name="ck_run_content_mode"
    ),
)
sa.Index("ix_analysis_run_created_at", analysis_run.c.created_at)
sa.Index("ix_analysis_run_thread_id", analysis_run.c.thread_id)
feedback = sa.Table(
    "feedback",
    metadata,
    sa.Column("feedback_id", UUID(as_uuid=True), primary_key=True),
    sa.Column(
        "request_id",
        UUID(as_uuid=True),
        sa.ForeignKey("analysis_run.request_id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("useful", sa.Boolean, nullable=False),
    sa.Column("comment", sa.String(2000)),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)
sa.Index("ix_feedback_request_id", feedback.c.request_id)
