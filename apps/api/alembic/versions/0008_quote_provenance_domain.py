"""Add quote and field-level provenance persistence.

Revision ID: 0008_quote_provenance_domain
Revises: 0007_supplier_explanation_steps
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008_quote_provenance_domain"
down_revision: str | None = "0007_supplier_explanation_steps"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("revision", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("entry_type IN ('MANUAL', 'PDF')", name="ck_quotes_entry_type"),
        sa.CheckConstraint(
            "status IN ('PROCESSING', 'NEEDS_REVIEW', 'CONFIRMED', 'FAILED')",
            name="ck_quotes_status",
        ),
        sa.CheckConstraint("revision >= 0", name="ck_quotes_revision"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "supplier_id", name="uq_quotes_project_supplier"),
    )
    op.create_table(
        "quote_values",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field_key", sa.String(length=64), nullable=False),
        sa.Column("current_value", postgresql.JSONB(), nullable=True),
        sa.Column("current_origin", sa.String(length=20), nullable=False),
        sa.Column("ai_extracted_value", postgresql.JSONB(), nullable=True),
        sa.Column("uncertainty", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "current_origin IN ('AI_EXTRACTED', 'USER_CORRECTED', 'USER_ENTERED')",
            name="ck_quote_values_current_origin",
        ),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quote_id", "field_key", name="uq_quote_values_quote_field"),
    )
    op.execute(sa.text("""
        CREATE FUNCTION prevent_quote_extraction_change() RETURNS trigger AS $$
        BEGIN
            IF OLD.ai_extracted_value IS NOT NULL
               AND NEW.ai_extracted_value IS DISTINCT FROM OLD.ai_extracted_value THEN
                RAISE EXCEPTION 'Stored AI-extracted quote value cannot be changed';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """))
    op.execute(sa.text("""
        CREATE TRIGGER quote_extraction_immutable
        BEFORE UPDATE ON quote_values
        FOR EACH ROW EXECUTE FUNCTION prevent_quote_extraction_change()
    """))


def downgrade() -> None:
    op.execute(sa.text("DROP TRIGGER IF EXISTS quote_extraction_immutable ON quote_values"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS prevent_quote_extraction_change()"))
    op.drop_table("quote_values")
    op.drop_table("quotes")
