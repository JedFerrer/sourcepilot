"""Add minimal ordered M2-U6 analyst run steps.

Revision ID: 0007_supplier_explanation_steps
Revises: 0006_project_supplier_review
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_supplier_explanation_steps"
down_revision: str | None = "0006_project_supplier_review"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "supplier_explanation_run_steps",
        sa.Column("air_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["air_run_id"], ["ai_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("air_run_id", "sequence"),
    )


def downgrade() -> None:
    op.drop_table("supplier_explanation_run_steps")
