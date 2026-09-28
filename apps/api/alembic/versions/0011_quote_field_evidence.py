"""Persist document-block citations for extracted quote fields.

Revision ID: 0011_quote_field_evidence
Revises: 0010_document_blocks
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0011_quote_field_evidence"
down_revision: str | None = "0010_document_blocks"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quote_field_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_value_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_block_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_value", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["quote_value_id"], ["quote_values.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_block_id"], ["document_blocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quote_field_evidence_quote_value_id", "quote_field_evidence", ["quote_value_id"])


def downgrade() -> None:
    op.drop_index("ix_quote_field_evidence_quote_value_id", table_name="quote_field_evidence")
    op.drop_table("quote_field_evidence")
