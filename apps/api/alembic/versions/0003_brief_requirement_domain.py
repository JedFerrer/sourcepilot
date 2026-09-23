"""Add Brief and Requirement persistence.

Revision ID: 0003_brief_requirement_domain
Revises: 0002_ai_run_foundation
Create Date: 2026-09-23

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_brief_requirement_domain"
down_revision: str | None = "0002_ai_run_foundation"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("brief_revision", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.create_table(
        "briefs",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("destination", sa.String(length=255), nullable=True),
        sa.Column("delivery_target", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("target_unit_price", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column(
            "status", sa.String(length=32), server_default=sa.text("'IN_PROGRESS'"), nullable=False
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("quantity > 0", name="ck_briefs_quantity_positive"),
        sa.CheckConstraint("target_unit_price > 0", name="ck_briefs_target_unit_price_positive"),
        sa.CheckConstraint(
            "status IN ('IN_PROGRESS', 'READY_FOR_REVIEW', 'APPROVED')",
            name="ck_briefs_status",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("project_id"),
    )
    op.create_table(
        "requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("importance", sa.String(length=32), nullable=False),
        sa.Column("expected_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "kind IN ('MATERIAL', 'CERTIFICATION', 'MOQ', 'QUANTITY', 'UNIT_PRICE', "
            "'PRODUCTION_LEAD_TIME', 'DELIVERY', 'CAPABILITY', 'INFORMATIONAL')",
            name="ck_requirements_kind",
        ),
        sa.CheckConstraint(
            "importance IN ('REQUIRED', 'PREFERRED', 'INFORMATIONAL')",
            name="ck_requirements_importance",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_requirements_project_id", "requirements", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_requirements_project_id", table_name="requirements")
    op.drop_table("requirements")
    op.drop_table("briefs")
    op.drop_column("projects", "brief_revision")
