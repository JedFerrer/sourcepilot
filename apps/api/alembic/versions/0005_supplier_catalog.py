"""Add the synthetic supplier catalog.

Revision ID: 0005_supplier_catalog
Revises: 0004_nullable_importance
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_supplier_catalog"
down_revision: str | None = "0004_nullable_importance"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("general_moq", sa.Integer(), nullable=True),
        sa.Column("general_lead_time_days", sa.Integer(), nullable=True),
        sa.Column("indicative_price_amount", sa.Numeric(12, 4), nullable=True),
        sa.Column("indicative_price_currency", sa.String(3), nullable=True),
        sa.CheckConstraint("general_moq > 0", name="ck_suppliers_general_moq_positive"),
        sa.CheckConstraint("general_lead_time_days > 0", name="ck_suppliers_lead_time_positive"),
        sa.CheckConstraint("indicative_price_amount > 0", name="ck_suppliers_price_positive"),
        sa.CheckConstraint(
            "(indicative_price_amount IS NULL) = (indicative_price_currency IS NULL)",
            name="ck_suppliers_price_currency_pair",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "supplier_capabilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("capability_kind", sa.String(40), nullable=False),
        sa.Column("value", sa.String(255), nullable=False),
        sa.CheckConstraint(
            "capability_kind IN ('PRODUCT_CATEGORY', 'MATERIAL', 'CERTIFICATION', "
            "'CUSTOM_BRANDING', 'BRANDING_METHOD', 'PRODUCT_FEATURE', "
            "'MANUFACTURING_CAPABILITY')",
            name="ck_supplier_capabilities_kind",
        ),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_supplier_capabilities_supplier_id", "supplier_capabilities", ["supplier_id"]
    )
    op.create_table(
        "supplier_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_key", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_label", sa.String(255), nullable=False),
        sa.Column("source_reference", sa.String(255), nullable=True),
        sa.Column("evidence_text", sa.Text(), nullable=False),
        sa.Column("evidence_state", sa.String(20), nullable=False),
        sa.CheckConstraint(
            "evidence_state IN ('SUPPORTS', 'CONTRADICTS', 'PARTIAL', 'UNKNOWN')",
            name="ck_supplier_evidence_state",
        ),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_supplier_evidence_supplier_id", "supplier_evidence", ["supplier_id"])
    op.create_index("ix_supplier_evidence_claim_key", "supplier_evidence", ["claim_key"])


def downgrade() -> None:
    op.drop_index("ix_supplier_evidence_claim_key", table_name="supplier_evidence")
    op.drop_index("ix_supplier_evidence_supplier_id", table_name="supplier_evidence")
    op.drop_table("supplier_evidence")
    op.drop_index("ix_supplier_capabilities_supplier_id", table_name="supplier_capabilities")
    op.drop_table("supplier_capabilities")
    op.drop_table("suppliers")
