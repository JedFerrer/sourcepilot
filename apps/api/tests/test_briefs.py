from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import Engine, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sourcepilot.briefs.domain import (
    BriefStatus,
    CapabilityKey,
    InformationalSubject,
    RequirementImportance,
    RequirementKind,
    validate_delivery_target,
    validate_requirement_expected_value,
)
from sourcepilot.briefs.service import increment_brief_revision
from sourcepilot.persistence.models import Brief, DemoSession, Project, Requirement
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
def reset_brief_database(test_database_url: str) -> Iterator[None]:
    reset_test_database(test_database_url)
    yield
    reset_test_database(test_database_url)


@pytest.fixture
def database_session(test_engine: Engine) -> Iterator[Session]:
    yield from database_session_for_engine(test_engine)


def make_project() -> Project:
    now = datetime.now(UTC)
    return Project(
        demo_session=DemoSession(
            opaque_token="brief-session",
            last_seen_at=now,
            expires_at=now + timedelta(hours=1),
        ),
        name="Brief project",
        original_request="Source cosmetic travel bags.",
    )


def test_project_persists_one_structured_brief_and_bounded_requirements(
    database_session: Session,
) -> None:
    project = make_project()
    brief = Brief(
        project=project,
        product_name="Cosmetic travel bag",
        category="Travel bags",
        quantity=2_000,
        destination="Sydney",
        delivery_target={"kind": "PERIOD", "label": "Before November", "start_date": None, "end_date": None},
        target_unit_price=Decimal("5.0000"),
        status=BriefStatus.IN_PROGRESS,
    )
    requirements = [
        Requirement(
            project=project,
            kind=RequirementKind.MATERIAL,
            importance=RequirementImportance.REQUIRED,
            expected_value={"value": " Recycled Polyester "},
        ),
        Requirement(
            project=project,
            kind=RequirementKind.CERTIFICATION,
            importance=RequirementImportance.PREFERRED,
            expected_value={"value": "GRS"},
        ),
        Requirement(
            project=project,
            kind=RequirementKind.MOQ,
            importance=RequirementImportance.REQUIRED,
            expected_value={"quantity": 500},
        ),
        Requirement(
            project=project,
            kind=RequirementKind.QUANTITY,
            importance=RequirementImportance.REQUIRED,
            expected_value={"quantity": 2_000},
        ),
        Requirement(
            project=project,
            kind=RequirementKind.UNIT_PRICE,
            importance=RequirementImportance.PREFERRED,
            expected_value={"amount": "5.00", "currency": "USD"},
        ),
        Requirement(
            project=project,
            kind=RequirementKind.PRODUCTION_LEAD_TIME,
            importance=RequirementImportance.PREFERRED,
            expected_value={"max_days": 30},
        ),
        Requirement(
            project=project,
            kind=RequirementKind.DELIVERY,
            importance=RequirementImportance.REQUIRED,
            expected_value={"kind": "DATE", "date": "2026-11-01"},
        ),
        Requirement(
            project=project,
            kind=RequirementKind.CAPABILITY,
            importance=RequirementImportance.REQUIRED,
            expected_value={"capability_key": "CUSTOM_BRANDING", "value": True},
        ),
        Requirement(
            project=project,
            kind=RequirementKind.INFORMATIONAL,
            importance=RequirementImportance.INFORMATIONAL,
            expected_value={"subject": "PACKAGING", "text": "Premium retail box"},
        ),
    ]
    database_session.add_all([project, brief, *requirements])
    database_session.commit()
    project_id = project.id
    requirement_ids = {requirement.id for requirement in requirements}
    database_session.expire_all()

    reloaded = database_session.get(Project, project_id)

    assert reloaded is not None
    assert reloaded.brief_revision == 0
    assert reloaded.brief is not None
    assert reloaded.brief.target_unit_price == Decimal("5.0000")
    assert reloaded.brief.delivery_target == {
        "kind": "PERIOD",
        "label": "Before November",
        "start_date": None,
        "end_date": None,
    }
    assert {requirement.id for requirement in reloaded.requirements} == requirement_ids
    assert {requirement.kind for requirement in reloaded.requirements} == {
        kind.value for kind in RequirementKind
    }
    assert reloaded.requirements[0].project_id == reloaded.id
    material = next(requirement for requirement in reloaded.requirements if requirement.kind == "MATERIAL")
    assert material.expected_value == {"value": "recycled polyester"}


@pytest.mark.parametrize(
    ("capability_key", "value"),
    [
        (CapabilityKey.PRODUCT_CATEGORY, "Cosmetic Bags"),
        (CapabilityKey.CUSTOM_BRANDING, True),
        (CapabilityKey.BRANDING_METHOD, "Screen Print"),
        (CapabilityKey.PRODUCT_FEATURE, "Water resistant"),
        (CapabilityKey.MANUFACTURING_CAPABILITY, "Welding"),
    ],
)
def test_capability_values_are_limited_to_the_approved_keys(
    database_session: Session, capability_key: CapabilityKey, value: bool | str
) -> None:
    project = make_project()
    requirement = Requirement(
        project=project,
        kind=RequirementKind.CAPABILITY,
        importance=RequirementImportance.REQUIRED,
        expected_value={"capability_key": capability_key.value, "value": value},
    )
    database_session.add_all([project, requirement])
    database_session.commit()

    assert requirement.expected_value["capability_key"] == capability_key.value


@pytest.mark.parametrize("subject", list(InformationalSubject))
def test_informational_values_are_limited_to_the_approved_subjects(
    database_session: Session, subject: InformationalSubject
) -> None:
    project = make_project()
    requirement = Requirement(
        project=project,
        kind=RequirementKind.INFORMATIONAL,
        importance=RequirementImportance.INFORMATIONAL,
        expected_value={"subject": subject.value, "text": "Contextual detail"},
    )
    database_session.add_all([project, requirement])
    database_session.commit()

    assert requirement.expected_value == {"subject": subject.value, "text": "Contextual detail"}


@pytest.mark.parametrize(
    "delivery_target",
    [
        {"kind": "DATE", "date": "2026-11-01"},
        {"kind": "PERIOD", "label": "Before November", "start_date": None, "end_date": None},
        {
            "kind": "PERIOD",
            "label": "November window",
            "start_date": "2026-11-01",
            "end_date": "2026-11-30",
        },
    ],
)
def test_delivery_target_accepts_only_approved_date_or_period_shapes(
    delivery_target: dict[str, object]
) -> None:
    assert validate_delivery_target(delivery_target) == delivery_target


@pytest.mark.parametrize(
    "delivery_target",
    [
        {"kind": "DATE", "date": "2026-11-01", "extra": "ignored"},
        {
            "kind": "PERIOD", "label": "November", "start_date": None,
            "end_date": None, "extra": "ignored",
        },
    ],
)
def test_delivery_target_rejects_extra_json_keys(delivery_target: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        validate_delivery_target(delivery_target)


def test_requirement_rejects_extra_json_keys() -> None:
    with pytest.raises(ValueError):
        validate_requirement_expected_value(
            RequirementKind.MATERIAL, {"value": "polyester", "extra": "ignored"}
        )


@pytest.mark.parametrize(
    ("kind", "expected_value"),
    [
        (RequirementKind.MATERIAL, {"value": ""}),
        (RequirementKind.MOQ, {"quantity": 0}),
        (RequirementKind.UNIT_PRICE, {"amount": 5}),
        (RequirementKind.PRODUCTION_LEAD_TIME, {"max_days": True}),
        (RequirementKind.DELIVERY, {"kind": "DATE", "date": "November"}),
        (RequirementKind.CAPABILITY, {"capability_key": "UNBOUNDED", "value": "x"}),
        (RequirementKind.INFORMATIONAL, {"subject": "FREEFORM", "text": "x"}),
    ],
)
def test_invalid_bounded_requirement_payloads_cannot_persist(
    database_session: Session, kind: RequirementKind, expected_value: dict[str, object]
) -> None:
    project = make_project()
    requirement = Requirement(
        project=project,
        kind=kind,
        importance=RequirementImportance.REQUIRED,
        expected_value=expected_value,
    )
    database_session.add_all([project, requirement])

    with pytest.raises(ValueError):
        database_session.commit()
    database_session.rollback()


def test_brief_rejects_non_positive_quantity(database_session: Session) -> None:
    project = make_project()
    brief = Brief(project=project, quantity=0)
    database_session.add_all([project, brief])

    with pytest.raises(ValueError, match="quantity"):
        database_session.commit()
    database_session.rollback()


def test_brief_rejects_floating_point_price(database_session: Session) -> None:
    project = make_project()
    brief = Brief(project=project, target_unit_price=5.0)
    database_session.add_all([project, brief])

    with pytest.raises(ValueError, match="Decimal"):
        database_session.commit()
    database_session.rollback()


@pytest.mark.parametrize("price", [Decimal("0.0001"), Decimal("99999999.9999")])
def test_brief_price_round_trips_at_numeric_boundaries(
    database_session: Session, price: Decimal
) -> None:
    project = make_project()
    brief = Brief(project=project, target_unit_price=price)
    database_session.add_all([project, brief])
    database_session.commit()
    database_session.expire_all()

    reloaded = database_session.get(Brief, project.id)
    assert reloaded is not None
    assert reloaded.target_unit_price == price


@pytest.mark.parametrize(
    ("price", "message"),
    [
        (Decimal("0.00001"), "fractional digits"),
        (Decimal("1.00000"), "fractional digits"),
        (Decimal("100000000.0000"), "precision"),
        (Decimal("Infinity"), "positive finite"),
        (Decimal("NaN"), "positive finite"),
        (Decimal(0), "positive finite"),
    ],
)
def test_brief_rejects_prices_outside_numeric_bounds(
    database_session: Session, price: Decimal, message: str
) -> None:
    project = make_project()
    database_session.add_all([project, Brief(project=project, target_unit_price=price)])

    with pytest.raises(ValueError, match=message):
        database_session.commit()
    database_session.rollback()


def test_brief_status_defaults_to_in_progress(database_session: Session) -> None:
    project = make_project()
    database_session.add_all([project, Brief(project=project)])
    database_session.commit()
    database_session.expire_all()

    reloaded = database_session.get(Brief, project.id)
    assert reloaded is not None
    assert reloaded.status == BriefStatus.IN_PROGRESS.value


def test_duplicate_brief_for_project_is_rejected(database_session: Session) -> None:
    project = make_project()
    database_session.add_all([project, Brief(project=project)])
    database_session.commit()
    project_id = project.id
    database_session.expunge_all()
    database_session.add(Brief(project_id=project_id))

    with pytest.raises(IntegrityError):
        database_session.commit()
    database_session.rollback()


def test_revision_increment_is_explicit(database_session: Session) -> None:
    project = make_project()
    database_session.add(project)
    database_session.commit()

    increment_brief_revision(database_session, project)
    database_session.commit()
    database_session.refresh(project)

    assert project.brief_revision == 1


def test_project_deletion_cascades_to_brief_and_requirements(database_session: Session) -> None:
    project = make_project()
    brief = Brief(project=project)
    requirement = Requirement(
        project=project,
        kind=RequirementKind.INFORMATIONAL,
        importance=RequirementImportance.INFORMATIONAL,
        expected_value={"subject": "OTHER_CONTEXT", "text": "Private context"},
    )
    database_session.add_all([project, brief, requirement])
    database_session.commit()
    project_id = project.id
    requirement_id = requirement.id

    database_session.execute(delete(Project).where(Project.id == project_id))
    database_session.commit()
    database_session.expire_all()

    assert database_session.get(Brief, project_id) is None
    assert database_session.get(Requirement, requirement_id) is None
