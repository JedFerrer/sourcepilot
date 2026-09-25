"""Read-only access to the curated supplier catalog."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from sourcepilot.persistence.models import Supplier, SupplierCapability


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


def suppliers_in_category(session: Session, category: str) -> list[Supplier]:
    """Fetch structured catalog matches with detail for candidate ordering."""
    statement = (
        select(Supplier)
        .where(
            select(SupplierCapability.id)
            .where(
                SupplierCapability.supplier_id == Supplier.id,
                SupplierCapability.capability_kind == "PRODUCT_CATEGORY",
                func.lower(SupplierCapability.value) == category,
            )
            .exists()
        )
        .options(selectinload(Supplier.capabilities))
        .order_by(Supplier.name, Supplier.id)
    )
    suppliers = list(session.scalars(statement).all())
    for supplier in suppliers:
        supplier.capabilities.sort(key=lambda item: (item.capability_kind, item.value, item.id))
    return suppliers
