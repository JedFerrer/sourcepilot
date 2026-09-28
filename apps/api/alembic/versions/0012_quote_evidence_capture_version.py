"""Mark PDF drafts finalized with U8 evidence persistence.

Revision ID: 0012_evidence_capture_marker
Revises: 0011_quote_field_evidence
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012_evidence_capture_marker"
down_revision: str | None = "0011_quote_field_evidence"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("quote_documents", sa.Column("evidence_capture_version", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("quote_documents", "evidence_capture_version")
