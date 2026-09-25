"""Persist project supplier review and requirement evaluations.

Revision ID: 0006_project_supplier_review
Revises: 0005_supplier_catalog
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_project_supplier_review"
down_revision: str | None = "0005_supplier_catalog"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_suppliers",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shortlisted", sa.Boolean(), nullable=False),
        sa.Column("dismissed", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("evaluated_against_brief_revision", sa.Integer(), nullable=False),
        sa.CheckConstraint("evaluated_against_brief_revision >= 0", name="ck_project_suppliers_revision"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("project_id", "supplier_id"),
    )
    op.create_table(
        "requirement_evaluations",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("resolved_source_type", sa.String(50), nullable=True),
        sa.Column("resolved_fact_reference", sa.String(255), nullable=True),
        sa.Column("evidence_ids", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint(
            "status IN ('MEETS', 'DOES_NOT_MEET', 'UNKNOWN', 'CONFLICT')",
            name="ck_requirement_evaluations_status",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "supplier_id"],
            ["project_suppliers.project_id", "project_suppliers.supplier_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["requirement_id"], ["requirements.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("project_id", "supplier_id", "requirement_id"),
    )


def downgrade() -> None:
    op.drop_table("requirement_evaluations")
    op.drop_table("project_suppliers")
