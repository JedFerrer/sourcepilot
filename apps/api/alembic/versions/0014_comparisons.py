"""Store revision-aware deterministic comparison snapshots.

Revision ID: 0014_comparisons
Revises: 0013_active_quote_document
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "0014_comparisons"
down_revision: str | None = "0013_active_quote_document"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "comparisons",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("brief_revision", sa.Integer(), nullable=False),
        sa.Column("quote_revision_snapshot", JSONB(), nullable=False),
        sa.Column("comparison_payload", JSONB(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("stale", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint("brief_revision >= 0", name="ck_comparisons_brief_revision"),
    )
    op.create_index("ix_comparisons_project_id", "comparisons", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_comparisons_project_id", table_name="comparisons")
    op.drop_table("comparisons")
