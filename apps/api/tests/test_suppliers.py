from __future__ import annotations

from collections.abc import Iterator
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, inspect, select
from sqlalchemy.orm import Session

from sourcepilot.persistence.models import (
    DemoSession,
    Project,
    Supplier,
    SupplierCapability,
    SupplierEvidence,
)
from sourcepilot.suppliers import seed as supplier_seed
from sourcepilot.suppliers.repository import get_supplier, list_suppliers
from sourcepilot.suppliers.seed import fixture_id, load_fixture_data, seed_suppliers
from tests.conftest import database_session_for_engine
from tests.database_test_support import (
    create_test_engine,
    persistence_test_database_url_from_environment,
    reset_test_database,
)


@pytest.fixture(scope="module")
def test_database_url() -> str:
    return persistence_test_database_url_from_environment()


@pytest.fixture(scope="module")
def test_engine(test_database_url: str) -> Iterator[Engine]:
    engine = create_test_engine(test_database_url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(autouse=True)
def reset_supplier_database(test_database_url: str) -> Iterator[None]:
    reset_test_database(test_database_url)
    yield
    reset_test_database(test_database_url)


@pytest.fixture
def database_session(test_engine: Engine) -> Iterator[Session]:
    yield from database_session_for_engine(test_engine)


def test_fixture_scenarios_and_fictional_notice() -> None:
    data = load_fixture_data()
    fixtures = data["suppliers"]
    assert len(fixtures) == 8
    assert "no real manufacturer" in data["synthetic_notice"].lower()
    assert len({row["key"] for row in fixtures}) == 8
    assert len({fixture_id("supplier", row["key"]) for row in fixtures}) == 8
    assert all("Fictional" in row["description"] for row in fixtures)

    by_key = {row["key"]: row for row in fixtures}
    assert by_key["harbor-pouch-works"]["general_moq"] <= 2000
    assert by_key["cedar-pack-co"]["general_moq"] > 2000
    assert by_key["moss-thread-bags"]["indicative_price_amount"] is None
    assert not any(
        item[0] == "certification:grs:current" for item in by_key["moss-thread-bags"]["evidence"]
    )
    conflict = [
        item
        for item in by_key["sunrise-textile-lab"]["evidence"]
        if item[0] == "certification:grs:current"
    ]
    assert {item[4] for item in conflict} == {"SUPPORTS", "CONTRADICTS"}
    assert by_key["coastal-home-textiles"]["capabilities"][0] == [
        "PRODUCT_CATEGORY",
        "home textile pouch",
    ]


def test_migration_creates_supplier_tables_and_constraints(test_engine: Engine) -> None:
    inspector = inspect(test_engine)
    assert {"suppliers", "supplier_capabilities", "supplier_evidence"}.issubset(
        inspector.get_table_names()
    )
    assert {"id", "name", "country", "general_moq", "indicative_price_currency"}.issubset(
        {column["name"] for column in inspector.get_columns("suppliers")}
    )
    assert any(
        foreign_key["referred_table"] == "suppliers"
        for foreign_key in inspector.get_foreign_keys("supplier_evidence")
    )
    assert any(
        constraint["name"] == "ck_suppliers_price_currency_pair"
        for constraint in inspector.get_check_constraints("suppliers")
    )


def test_seed_is_repeatable_and_preserves_unrelated_records(database_session: Session) -> None:
    unrelated = Supplier(
        id=uuid4(),
        name="Independent fictional supplier",
        country="Peru",
        description="Unrelated test catalog record.",
    )
    database_session.add(unrelated)
    database_session.commit()
    assert seed_suppliers(database_session) == 8
    initial_ids = {
        model: set(database_session.scalars(select(model.id)).all())
        for model in (Supplier, SupplierCapability, SupplierEvidence)
    }
    initial_evidence = {
        row.id: (row.claim_key, row.source_label, row.evidence_text, row.evidence_state)
        for row in database_session.scalars(select(SupplierEvidence)).all()
    }
    database_session.commit()
    assert seed_suppliers(database_session) == 8
    assert initial_ids == {
        model: set(database_session.scalars(select(model.id)).all())
        for model in (Supplier, SupplierCapability, SupplierEvidence)
    }
    assert initial_evidence == {
        row.id: (row.claim_key, row.source_label, row.evidence_text, row.evidence_state)
        for row in database_session.scalars(select(SupplierEvidence)).all()
    }
    assert database_session.scalar(select(func.count(Supplier.id))) == 9
    assert database_session.get(Supplier, unrelated.id) is not None


def test_reseed_removes_fixture_children_removed_from_definition(
    database_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixtures = deepcopy(load_fixture_data())
    supplier = next(row for row in fixtures["suppliers"] if row["key"] == "harbor-pouch-works")
    supplier_id = fixture_id("supplier", supplier["key"])
    removed_capability = supplier["capabilities"].pop()
    removed_evidence = supplier["evidence"].pop()
    seed_suppliers(database_session)
    database_session.commit()
    monkeypatch.setattr(supplier_seed, "load_fixture_data", lambda: fixtures)
    seed_suppliers(database_session)
    database_session.expire_all()

    capabilities = database_session.scalars(
        select(SupplierCapability).where(SupplierCapability.supplier_id == supplier_id)
    ).all()
    evidence = database_session.scalars(
        select(SupplierEvidence).where(SupplierEvidence.supplier_id == supplier_id)
    ).all()
    assert len(capabilities) == len(supplier["capabilities"])
    assert len(evidence) == len(supplier["evidence"])
    assert (
        database_session.get(
            SupplierCapability,
            fixture_id(
                "capability", f"{supplier['key']}:{removed_capability[0]}:{removed_capability[1]}"
            ),
        )
        is None
    )
    assert (
        database_session.get(
            SupplierEvidence,
            fixture_id("evidence", f"{supplier['key']}:{removed_evidence[5]}"),
        )
        is None
    )
    remaining_ids = {
        model: set(database_session.scalars(select(model.id)).all())
        for model in (SupplierCapability, SupplierEvidence)
    }
    database_session.commit()
    seed_suppliers(database_session)
    assert remaining_ids == {
        model: set(database_session.scalars(select(model.id)).all())
        for model in (SupplierCapability, SupplierEvidence)
    }
    assert database_session.scalar(select(func.count(Supplier.id))) == 8


def test_reordering_evidence_preserves_identity_and_updates_its_own_claim(
    database_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixtures = deepcopy(load_fixture_data())
    supplier = next(row for row in fixtures["suppliers"] if row["key"] == "sunrise-textile-lab")
    supplier_id = fixture_id("supplier", supplier["key"])
    seed_suppliers(database_session)
    before = {
        row.id: (row.claim_key, row.source_label, row.evidence_text, row.evidence_state)
        for row in database_session.scalars(
            select(SupplierEvidence).where(SupplierEvidence.supplier_id == supplier_id)
        ).all()
    }
    database_session.commit()

    supplier["evidence"].reverse()
    supplier["evidence"][0][3] = "Updated synthetic register B statement."
    monkeypatch.setattr(supplier_seed, "load_fixture_data", lambda: fixtures)
    seed_suppliers(database_session)
    database_session.expire_all()
    after = {
        row.id: (row.claim_key, row.source_label, row.evidence_text, row.evidence_state)
        for row in database_session.scalars(
            select(SupplierEvidence).where(SupplierEvidence.supplier_id == supplier_id)
        ).all()
    }
    expected = before.copy()
    changed_id = fixture_id("evidence", "sunrise-textile-lab:grs-register-b")
    original = before[changed_id]
    expected[changed_id] = (
        original[0],
        original[1],
        "Updated synthetic register B statement.",
        original[3],
    )
    assert after == expected
    changed = database_session.get(SupplierEvidence, changed_id)
    assert changed is not None
    assert changed.evidence_text == "Updated synthetic register B statement."


def test_repository_returns_ordered_catalog_and_both_conflict_records(
    database_session: Session,
) -> None:
    seed_suppliers(database_session)
    suppliers = list_suppliers(database_session)
    assert len(suppliers) == 8
    assert [row.name for row in suppliers] == sorted(row.name for row in suppliers)
    conflict = get_supplier(database_session, fixture_id("supplier", "sunrise-textile-lab"))
    assert conflict is not None
    records = [row for row in conflict.evidence if row.claim_key == "certification:grs:current"]
    assert len(records) == 2
    assert {row.evidence_state for row in records} == {"SUPPORTS", "CONTRADICTS"}
    unknown = get_supplier(database_session, fixture_id("supplier", "moss-thread-bags"))
    assert unknown is not None
    assert not any(row.claim_key == "certification:grs:current" for row in unknown.evidence)
    assert all(row.supplier_id == unknown.id for row in unknown.capabilities + unknown.evidence)
    assert get_supplier(database_session, uuid4()) is None


def test_supplier_migration_round_trip_preserves_existing_project(
    test_engine: Engine,
    test_database_url: str,
) -> None:
    from alembic import command
    from tests.database_test_support import alembic_config

    now = datetime.now(UTC)
    with Session(test_engine) as session:
        project = Project(
            demo_session=DemoSession(
                opaque_token="migration-preservation",
                last_seen_at=now,
                expires_at=now + timedelta(hours=1),
            ),
            name="Existing project",
            original_request="Source travel bags.",
        )
        session.add(project)
        session.commit()
        project_id = project.id

    config = alembic_config(test_database_url)
    command.downgrade(config, "0004_nullable_importance")
    assert "suppliers" not in inspect(test_engine).get_table_names()
    command.upgrade(config, "head")
    assert "suppliers" in inspect(test_engine).get_table_names()
    with Session(test_engine) as session:
        assert session.get(Project, project_id) is not None
