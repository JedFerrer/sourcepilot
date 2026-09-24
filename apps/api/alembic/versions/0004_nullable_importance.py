"""Allow extracted requirements to retain unstated importance.

Revision ID: 0004_nullable_importance
Revises: 0003_brief_requirement_domain
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_nullable_importance"
down_revision: str | None = "0003_brief_requirement_domain"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("requirements", "importance", nullable=True)


def downgrade() -> None:
    unknown_count = op.get_bind().execute(
        sa.text("SELECT count(*) FROM requirements WHERE importance IS NULL")
    ).scalar_one()
    if unknown_count:
        raise RuntimeError("Resolve unknown requirement importance before downgrading.")
    op.alter_column("requirements", "importance", nullable=False)
