"""Identify the single active PDF document without guessing historical ownership.

Revision ID: 0013_active_quote_document
Revises: 0012_evidence_capture_marker
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013_active_quote_document"
down_revision: str | None = "0012_evidence_capture_marker"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    ambiguous = connection.execute(sa.text("""
        SELECT q.id, count(d.id) AS document_count
        FROM quotes q LEFT JOIN quote_documents d ON d.quote_id = q.id
        WHERE q.entry_type = 'PDF'
        GROUP BY q.id HAVING count(d.id) <> 1
        LIMIT 1
    """)).first()
    if ambiguous is not None:
        raise RuntimeError(
            "Cannot identify the canonical PDF document for every Quote; "
            "resolve missing or multiple documents before migrating."
        )
    manual_document = connection.execute(sa.text("""
        SELECT d.id FROM quote_documents d JOIN quotes q ON q.id = d.quote_id
        WHERE q.entry_type = 'MANUAL' LIMIT 1
    """)).first()
    if manual_document is not None:
        raise RuntimeError("A manual Quote has a PDF document; resolve it before migrating.")
    op.add_column("quote_documents", sa.Column(
        "is_active", sa.Boolean(), nullable=False, server_default=sa.false()
    ))
    connection.execute(sa.text("""
        UPDATE quote_documents SET is_active = true
        WHERE quote_id IN (SELECT id FROM quotes WHERE entry_type = 'PDF')
    """))
    op.create_index(
        "uq_quote_documents_one_active_per_quote", "quote_documents", ["quote_id"],
        unique=True, postgresql_where=sa.text("is_active"),
    )


def downgrade() -> None:
    op.drop_index("uq_quote_documents_one_active_per_quote", table_name="quote_documents")
    op.drop_column("quote_documents", "is_active")
