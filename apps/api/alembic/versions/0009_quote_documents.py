"""Add stored PDF quote document metadata.

Revision ID: 0009_quote_documents
Revises: 0008_quote_provenance_domain
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009_quote_documents"
down_revision: str | None = "0008_quote_provenance_domain"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quote_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(length=128), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("processing_status", sa.String(length=20), nullable=False),
        sa.Column("processing_attempts", sa.Integer(), nullable=False),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.CheckConstraint("processing_attempts >= 0", name="ck_quote_documents_attempts"),
        sa.CheckConstraint(
            "processing_status IN ('PROCESSING', 'NEEDS_REVIEW', 'CONFIRMED', 'FAILED')",
            name="ck_quote_documents_status",
        ),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key", name="uq_quote_documents_storage_key"),
    )


def downgrade() -> None:
    op.drop_table("quote_documents")
