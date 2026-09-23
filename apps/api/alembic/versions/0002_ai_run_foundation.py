"""Add application-owned AI run records.

Revision ID: 0002_ai_run_foundation
Revises: 0001_persistence_foundation
Create Date: 2026-09-23
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_ai_run_foundation"
down_revision: str | None = "0001_persistence_foundation"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("demo_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("operation", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("model_turn_count", sa.Integer(), nullable=True),
        sa.Column("tool_call_count", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("validation_status", sa.String(length=32), nullable=True),
        sa.Column("error_type", sa.String(length=100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["demo_session_id"], ["demo_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_runs_demo_session_id", "ai_runs", ["demo_session_id"])
    op.create_index("ix_ai_runs_project_id", "ai_runs", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_runs_project_id", table_name="ai_runs")
    op.drop_index("ix_ai_runs_demo_session_id", table_name="ai_runs")
    op.drop_table("ai_runs")
