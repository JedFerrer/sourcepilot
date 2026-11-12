from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from sourcepilot.briefs.domain import BriefStatus, RequirementImportance, RequirementKind
from sourcepilot.briefs.readiness import (
    BriefReadinessResult,
    ReadinessRequirement,
    evaluate_brief_readiness,
)
from sourcepilot.briefs.service import recalculate_brief_readiness
from sourcepilot.persistence.models import Brief, Requirement
from tests.conftest import database_session_for_engine
from tests.database_test_support import (
    create_test_engine,
    persistence_test_database_url_from_environment,
    reset_test_database,
)
from tests.factories import make_demo_session, make_project


def material() -> ReadinessRequirement:
    return ReadinessRequirement(RequirementKind.MATERIAL, {"value": "recycled polyester"})


def branding(value: bool = True) -> ReadinessRequirement:
    return ReadinessRequirement(
        RequirementKind.CAPABILITY,
        {"capability_key": "CUSTOM_BRANDING", "value": value},
    )


def evaluate(
    *,
    product_name: str | None = "Cosmetic travel bag",
    category: str | None = "Cosmetic travel bag",
    quantity: int | None = 2_000,
    destination: str | None = "Sydney",
    delivery_target: object = {"kind": "DATE", "date": "2026-11-01"},
    requirements: tuple[ReadinessRequirement, ...] = (material(), branding()),
) -> BriefReadinessResult:
    return evaluate_brief_readiness(
        product_name=product_name,
        category=category,
        quantity=quantity,
        destination=destination,
        delivery_target=delivery_target,
        requirements=requirements,
    )


def test_complete_demo_brief_is_ready_without_target_price() -> None:
    result = evaluate()
    assert result.status is BriefStatus.READY_FOR_REVIEW
    assert result.missing_fields == ()


def test_missing_field_keys_have_exact_order_and_reasons() -> None:
    result = evaluate(
        product_name=None,
        category="Travel bags",
        quantity=None,
        destination=None,
        delivery_target=None,
        requirements=(),
    )
    assert result.status is BriefStatus.IN_PROGRESS
    assert [item.field_key for item in result.missing_fields] == [
        "product_name",
        "quantity",
        "destination",
        "delivery_target",
        "requirement.material",
        "requirement.custom_branding",
    ]
    assert all(item.reason.strip() for item in result.missing_fields)


def test_each_missing_field_has_its_key_and_reason() -> None:
    cases = [
        (evaluate(product_name=None), "product_name", "Name the product to source."),
        (evaluate(category=None), "category", "Confirm the product category."),
        (evaluate(quantity=None), "quantity", "Enter a positive requested quantity."),
        (evaluate(destination=None), "destination", "Enter the delivery destination."),
        (evaluate(delivery_target=None), "delivery_target", "Enter a valid delivery target."),
        (
            evaluate(requirements=(branding(),)),
            "requirement.material",
            "Specify the material for the demo product.",
        ),
        (
            evaluate(requirements=(material(),)),
            "requirement.custom_branding",
            "State whether custom branding is required for the demo product.",
        ),
    ]
    for result, field_key, reason in cases:
        assert [(item.field_key, item.reason) for item in result.missing_fields] == [
            (field_key, reason)
        ]


@pytest.mark.parametrize("value", [None, "", " \t "])
def test_required_text_must_be_nonblank(value: str | None) -> None:
    for field in ("product_name", "category", "destination"):
        values: dict[str, str | None] = {
            "product_name": "Bag",
            "category": "Travel bags",
            "destination": "Sydney",
        }
        values[field] = value
        result = evaluate(
            product_name=values["product_name"],
            category=values["category"],
            destination=values["destination"],
        )
        assert [item.field_key for item in result.missing_fields] == [field]
        assert result.status is BriefStatus.IN_PROGRESS


def test_surrounding_whitespace_does_not_block_known_text() -> None:
    result = evaluate(
        product_name="  Cosmetic travel bag  ",
        category="  TRAVEL BAGS  ",
        destination="  Sydney  ",
    )
    assert result.status is BriefStatus.READY_FOR_REVIEW


@pytest.mark.parametrize("quantity", [None, 0, -1, True])
def test_quantity_must_be_positive_integer(quantity: int | None) -> None:
    result = evaluate(quantity=quantity)
    assert [item.field_key for item in result.missing_fields] == ["quantity"]


@pytest.mark.parametrize(
    "delivery_target",
    [
        {"kind": "DATE", "date": "2026-11-01"},
        {"kind": "PERIOD", "label": "Before November", "start_date": None, "end_date": None},
    ],
)
def test_both_valid_delivery_shapes_are_ready(delivery_target: dict[str, object]) -> None:
    assert evaluate(delivery_target=delivery_target).status is BriefStatus.READY_FOR_REVIEW


@pytest.mark.parametrize("delivery_target", [None, {}, {"kind": "DATE", "date": "November"}])
def test_missing_or_invalid_delivery_target_blocks(delivery_target: object) -> None:
    result = evaluate(delivery_target=delivery_target)
    assert [item.field_key for item in result.missing_fields] == ["delivery_target"]


@pytest.mark.parametrize(
    "category",
    [
        "Cosmetic bag",
        "Cosmetic bags",
        "Cosmetic travel bag",
        "Cosmetic travel bags",
        "Travel bags",
    ],
)
def test_exact_demo_aliases_require_material_and_branding(category: str) -> None:
    result = evaluate(category=category, requirements=())
    assert [item.field_key for item in result.missing_fields] == [
        "requirement.material",
        "requirement.custom_branding",
    ]


@pytest.mark.parametrize("category", [
    "Travel bag", "Cosmetic bag accessories", "Handbags", "bags", "pouches", "bottles",
])
def test_other_categories_have_no_demo_specific_gate(category: str) -> None:
    assert evaluate(category=category, requirements=()).status is BriefStatus.READY_FOR_REVIEW


def test_absent_category_has_only_its_own_missing_key() -> None:
    result = evaluate(category=None, requirements=())
    assert [item.field_key for item in result.missing_fields] == ["category"]


def test_false_branding_counts_as_answered() -> None:
    assert evaluate(requirements=(material(), branding(False))).status is BriefStatus.READY_FOR_REVIEW


def test_only_typed_capability_custom_branding_counts() -> None:
    wrong_facts = (
        material(),
        ReadinessRequirement(RequirementKind.INFORMATIONAL, {"subject": "BRANDING_NOTES", "text": "Logo"}),
        ReadinessRequirement(RequirementKind.CAPABILITY, {"capability_key": "BRANDING_METHOD", "value": "print"}),
        ReadinessRequirement(RequirementKind.CAPABILITY, {"capability_key": "CUSTOM_BRANDING", "value": "yes"}),
    )
    result = evaluate(requirements=wrong_facts)
    assert [item.field_key for item in result.missing_fields] == ["requirement.custom_branding"]


def test_invalid_material_does_not_count() -> None:
    result = evaluate(
        requirements=(ReadinessRequirement(RequirementKind.MATERIAL, {"value": " "}), branding())
    )
    assert [item.field_key for item in result.missing_fields] == ["requirement.material"]


def test_requirement_order_does_not_change_result() -> None:
    first = evaluate(requirements=(material(), branding()))
    second = evaluate(requirements=(branding(), material()))
    assert first == second


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


@pytest.fixture
def database_session(test_engine: Engine, test_database_url: str) -> Iterator[Session]:
    reset_test_database(test_database_url)
    try:
        yield from database_session_for_engine(test_engine)
    finally:
        reset_test_database(test_database_url)


def make_persisted_brief(database_session: Session) -> Brief:
    project = make_project(make_demo_session(), "Cosmetic bag")
    brief = Brief(
        project=project,
        product_name="Cosmetic travel bag",
        category="Travel bags",
        quantity=2_000,
        destination="Sydney",
        delivery_target={"kind": "DATE", "date": "2026-11-01"},
        target_unit_price=Decimal("5.0000"),
    )
    database_session.add_all([project, brief])
    database_session.commit()
    return brief


def persist_requirements(
    database_session: Session, brief: Brief, importance: RequirementImportance
) -> list[Requirement]:
    requirements = [
        Requirement(
            project=brief.project,
            kind=RequirementKind.MATERIAL,
            importance=importance,
            expected_value={"value": "recycled polyester"},
        ),
        Requirement(
            project=brief.project,
            kind=RequirementKind.CAPABILITY,
            importance=importance,
            expected_value={"capability_key": "CUSTOM_BRANDING", "value": False},
        ),
    ]
    database_session.add_all(requirements)
    database_session.commit()
    return requirements


def make_foreign_requirement(database_session: Session) -> Requirement:
    project = make_project(make_demo_session("foreign-session"), "Foreign project")
    requirement = Requirement(
        project=project,
        kind=RequirementKind.MATERIAL,
        importance=RequirementImportance.REQUIRED,
        expected_value={"value": "cotton"},
    )
    database_session.add_all([project, requirement])
    database_session.commit()
    return requirement


def test_application_rejects_foreign_only_requirements(database_session: Session) -> None:
    brief = make_persisted_brief(database_session)
    foreign_requirement = make_foreign_requirement(database_session)

    with pytest.raises(ValueError, match="all requirements must belong to the brief's project"):
        recalculate_brief_readiness(database_session, brief, [foreign_requirement])

    assert brief.status == BriefStatus.IN_PROGRESS.value


def test_application_rejects_mixed_project_requirements(database_session: Session) -> None:
    brief = make_persisted_brief(database_session)
    own_requirements = persist_requirements(database_session, brief, RequirementImportance.REQUIRED)
    foreign_requirement = make_foreign_requirement(database_session)

    with pytest.raises(ValueError, match="all requirements must belong to the brief's project"):
        recalculate_brief_readiness(database_session, brief, [*own_requirements, foreign_requirement])

    assert brief.status == BriefStatus.IN_PROGRESS.value


def test_application_accepts_same_project_requirements(database_session: Session) -> None:
    brief = make_persisted_brief(database_session)
    requirements = persist_requirements(database_session, brief, RequirementImportance.REQUIRED)

    result = recalculate_brief_readiness(database_session, brief, requirements)

    assert result.status is BriefStatus.READY_FOR_REVIEW
    assert brief.status == BriefStatus.READY_FOR_REVIEW.value


@pytest.mark.parametrize("importance", list(RequirementImportance))
def test_application_recalculates_both_directions_and_ignores_importance(
    database_session: Session, importance: RequirementImportance
) -> None:
    brief = make_persisted_brief(database_session)
    requirements = persist_requirements(database_session, brief, importance)

    result = recalculate_brief_readiness(database_session, brief, requirements)
    database_session.commit()
    database_session.refresh(brief)
    assert result.status is BriefStatus.READY_FOR_REVIEW
    assert brief.status == BriefStatus.READY_FOR_REVIEW.value

    brief.destination = "  "
    result = recalculate_brief_readiness(database_session, brief, requirements)
    database_session.commit()
    database_session.refresh(brief)
    assert result.status is BriefStatus.IN_PROGRESS
    assert [item.field_key for item in result.missing_fields] == ["destination"]
    assert brief.status == BriefStatus.IN_PROGRESS.value


def test_application_never_changes_approved_status(database_session: Session) -> None:
    brief = make_persisted_brief(database_session)
    brief.status = BriefStatus.APPROVED.value
    database_session.commit()

    result = recalculate_brief_readiness(database_session, brief, [])
    database_session.commit()
    database_session.refresh(brief)

    assert result.status is BriefStatus.IN_PROGRESS
    assert brief.status == BriefStatus.APPROVED.value


def test_application_can_recalculate_new_brief_before_initial_flush(
    database_session: Session,
) -> None:
    project = make_project(make_demo_session(), "New brief")
    brief = Brief(project=project, product_name="Bag")
    database_session.add_all([project, brief])

    result = recalculate_brief_readiness(database_session, brief, [])
    database_session.commit()
    database_session.refresh(brief)

    assert result.status is BriefStatus.IN_PROGRESS
    assert brief.status == BriefStatus.IN_PROGRESS.value
