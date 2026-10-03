"""Deterministic rules for changing the user's current preference."""

from uuid import UUID


class PreferredSupplierNotShortlistedError(ValueError):
    """A different supplier must belong to the project's current shortlist."""


def validate_preferred_supplier(
    supplier_id: UUID | None, *, current_supplier_id: UUID | None, shortlisted: bool,
) -> None:
    """Clearing and retaining a choice do not require renewed shortlist membership."""
    if supplier_id is None or supplier_id == current_supplier_id:
        return
    if not shortlisted:
        raise PreferredSupplierNotShortlistedError("Choose a supplier from this project's current shortlist.")
