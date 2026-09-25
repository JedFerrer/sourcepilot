"""Explicit, repeatable loading of fictional supplier fixtures."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid5

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from sourcepilot.persistence.database import application_session_factory
from sourcepilot.persistence.models import Supplier, SupplierCapability, SupplierEvidence

FIXTURE_PATH = Path(__file__).with_name("fixtures.json")
FIXTURE_NAMESPACE = UUID("9d3754f2-5d12-43f2-9305-79131066c655")


def fixture_id(kind: str, key: str) -> UUID:
    return uuid5(FIXTURE_NAMESPACE, f"{kind}:{key}")


def load_fixture_data() -> dict[str, Any]:
    data = cast(dict[str, Any], json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))
    if "fictional" not in data["synthetic_notice"].lower():
        raise ValueError("Supplier fixtures must explicitly state they are fictional")
    return data


def seed_suppliers(session: Session) -> int:
    """Reconcile fixture suppliers and their children; leave other suppliers untouched."""
    fixtures = load_fixture_data()["suppliers"]
    with session.begin():
        for record in fixtures:
            key = record["key"]
            supplier_id = fixture_id("supplier", key)
            supplier_values = {
                "id": supplier_id,
                "name": record["name"],
                "country": record["country"],
                "description": record["description"],
                "general_moq": record["general_moq"],
                "general_lead_time_days": record["general_lead_time_days"],
                "indicative_price_amount": (
                    Decimal(record["indicative_price_amount"])
                    if record["indicative_price_amount"] is not None
                    else None
                ),
                "indicative_price_currency": record["indicative_price_currency"],
            }
            supplier_insert = insert(Supplier).values(**supplier_values)
            session.execute(
                supplier_insert.on_conflict_do_update(
                    index_elements=[Supplier.id],
                    set_={name: value for name, value in supplier_values.items() if name != "id"},
                )
            )

            capability_ids = {
                fixture_id("capability", f"{key}:{kind}:{value}")
                for kind, value in record["capabilities"]
            }
            if len(capability_ids) != len(record["capabilities"]):
                raise ValueError(f"Duplicate capability in supplier fixture {key}")
            for kind, value in record["capabilities"]:
                capability_values = {
                    "id": fixture_id("capability", f"{key}:{kind}:{value}"),
                    "supplier_id": supplier_id,
                    "capability_kind": kind,
                    "value": value,
                }
                capability_insert = insert(SupplierCapability).values(**capability_values)
                session.execute(
                    capability_insert.on_conflict_do_update(
                        index_elements=[SupplierCapability.id],
                        set_={"supplier_id": supplier_id, "capability_kind": kind, "value": value},
                    )
                )

            evidence_ids = {
                fixture_id("evidence", f"{key}:{evidence[5]}") for evidence in record["evidence"]
            }
            if len(evidence_ids) != len(record["evidence"]):
                raise ValueError(f"Duplicate evidence key in supplier fixture {key}")
            for evidence in record["evidence"]:
                claim_key, source_type, source_label, evidence_text, state, evidence_key = evidence
                evidence_values = {
                    "id": fixture_id("evidence", f"{key}:{evidence_key}"),
                    "supplier_id": supplier_id,
                    "claim_key": claim_key,
                    "source_type": source_type,
                    "source_label": source_label,
                    "source_reference": None,
                    "evidence_text": evidence_text,
                    "evidence_state": state,
                }
                evidence_insert = insert(SupplierEvidence).values(**evidence_values)
                session.execute(
                    evidence_insert.on_conflict_do_update(
                        index_elements=[SupplierEvidence.id],
                        set_={
                            name: value for name, value in evidence_values.items() if name != "id"
                        },
                    )
                )
            session.execute(
                delete(SupplierCapability)
                .where(SupplierCapability.supplier_id == supplier_id)
                .where(SupplierCapability.id.not_in(capability_ids))
            )
            session.execute(
                delete(SupplierEvidence)
                .where(SupplierEvidence.supplier_id == supplier_id)
                .where(SupplierEvidence.id.not_in(evidence_ids))
            )
    return len(fixtures)


def main() -> None:
    with application_session_factory()() as session:
        count = seed_suppliers(session)
    print(f"Seeded {count} fictional suppliers.")


if __name__ == "__main__":
    main()
