"""Persist the current human supplier decision on projects."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0015_preferred_supplier"
down_revision: str | None = "0014_comparisons"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("preferred_supplier_id", UUID(as_uuid=True), nullable=True))
    op.add_column("projects", sa.Column("decision_notes", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_projects_preferred_supplier", "projects", "suppliers",
        ["preferred_supplier_id"], ["id"], ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_projects_preferred_supplier", "projects", type_="foreignkey")
    op.drop_column("projects", "decision_notes")
    op.drop_column("projects", "preferred_supplier_id")
