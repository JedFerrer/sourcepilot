"""Persist document-scoped PDF text blocks.

Revision ID: 0010_document_blocks
Revises: 0009_quote_documents
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0010_document_blocks"
down_revision: str | None = "0009_quote_documents"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_blocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("block_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.CheckConstraint("page_number > 0", name="ck_document_blocks_page_positive"),
        sa.CheckConstraint("block_number > 0", name="ck_document_blocks_number_positive"),
        sa.CheckConstraint("text ~ '[^[:space:]]'", name="ck_document_blocks_text_nonblank"),
        sa.ForeignKeyConstraint(["quote_document_id"], ["quote_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "quote_document_id", "page_number", "block_number",
            name="uq_document_blocks_document_page_number",
        ),
    )


def downgrade() -> None:
    op.drop_table("document_blocks")
