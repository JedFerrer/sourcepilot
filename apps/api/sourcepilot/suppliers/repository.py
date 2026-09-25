"""Read-only access to the curated supplier catalog."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from sourcepilot.persistence.models import Supplier


def list_suppliers(session: Session) -> list[Supplier]:
    """List suppliers with their catalog detail in stable name/ID order."""
    statement = (
        select(Supplier)
        .options(selectinload(Supplier.capabilities), selectinload(Supplier.evidence))
        .order_by(Supplier.name, Supplier.id)
    )
    suppliers = list(session.scalars(statement).all())
    for supplier in suppliers:
        supplier.capabilities.sort(key=lambda item: (item.capability_kind, item.value, item.id))
        supplier.evidence.sort(key=lambda item: (item.claim_key, item.source_label, item.id))
    return suppliers


def get_supplier(session: Session, supplier_id: UUID) -> Supplier | None:
    """Fetch one supplier and its capabilities and evidence."""
    statement = (
        select(Supplier)
        .where(Supplier.id == supplier_id)
        .options(selectinload(Supplier.capabilities), selectinload(Supplier.evidence))
    )
    supplier = session.scalar(statement)
    if supplier is not None:
        supplier.capabilities.sort(key=lambda item: (item.capability_kind, item.value, item.id))
        supplier.evidence.sort(key=lambda item: (item.claim_key, item.source_label, item.id))
    return supplier
