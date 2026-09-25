"""Exact supplier-stage evaluator and fixture regression tests."""

from uuid import UUID, uuid4

import pytest

from sourcepilot.briefs.domain import RequirementKind
from sourcepilot.suppliers.evaluation import (
    EvaluationEvidence,
    EvaluationRequirement,
    EvaluationStatus,
    SupplierEvaluationFacts,
    evaluate_supplier,
)
from sourcepilot.suppliers.seed import fixture_id, load_fixture_data


def _requirement(kind: RequirementKind, value: dict[str, object]) -> EvaluationRequirement:
    return EvaluationRequirement(uuid4(), kind, value)


def _evidence(claim: str, state: str, *, id: UUID | None = None) -> EvaluationEvidence:
    return EvaluationEvidence(id or uuid4(), claim, state)


def _supplier(
    *,
    capabilities: tuple[tuple[str, str], ...] = (),
    moq: int | None = None,
    evidence: tuple[EvaluationEvidence, ...] = (),
) -> SupplierEvaluationFacts:
    return SupplierEvaluationFacts(frozenset(capabilities), moq, evidence)


def _status(
    requirement: EvaluationRequirement, supplier: SupplierEvaluationFacts
) -> EvaluationStatus:
    return evaluate_supplier([requirement], requested_quantity=2000, supplier=supplier).results[0].status


@pytest.mark.parametrize(
    ("kind", "value", "claim", "capability"),
    [
        (RequirementKind.MATERIAL, "recycled polyester", "material:recycled polyester", "MATERIAL"),
        (RequirementKind.CERTIFICATION, "grs", "certification:grs:current", "CERTIFICATION"),
    ],
)
def test_material_and_certification_four_states(
    kind: RequirementKind, value: str, claim: str, capability: str
) -> None:
    requirement = _requirement(kind, {"value": value})
    fact = ((capability, value),)
    assert _status(requirement, _supplier(capabilities=fact)) is EvaluationStatus.UNKNOWN
    assert _status(requirement, _supplier(evidence=(_evidence(claim, "SUPPORTS"),))) is EvaluationStatus.UNKNOWN
    assert _status(
        requirement, _supplier(capabilities=fact, evidence=(_evidence(claim, "SUPPORTS"),))
    ) is EvaluationStatus.MEETS
    assert _status(
        requirement, _supplier(evidence=(_evidence(claim, "CONTRADICTS"),))
    ) is EvaluationStatus.DOES_NOT_MEET
    assert _status(
        requirement,
        _supplier(
            capabilities=fact,
            evidence=(_evidence(claim, "SUPPORTS"), _evidence(claim, "CONTRADICTS")),
        ),
    ) is EvaluationStatus.CONFLICT


def test_other_material_or_certification_is_not_negative_proof() -> None:
    requirement = _requirement(RequirementKind.MATERIAL, {"value": "recycled polyester"})
    supplier = _supplier(
        capabilities=(("MATERIAL", "cotton"),),
        evidence=(_evidence("material:cotton", "SUPPORTS"),),
    )
    assert _status(requirement, supplier) is EvaluationStatus.UNKNOWN


@pytest.mark.parametrize("state", ["PARTIAL", "UNKNOWN"])
def test_inconclusive_evidence_does_not_establish_a_claim(state: str) -> None:
    requirement = _requirement(RequirementKind.MATERIAL, {"value": "recycled polyester"})
    supplier = _supplier(
        capabilities=(("MATERIAL", "recycled polyester"),),
        evidence=(_evidence("material:recycled polyester", state),),
    )
    assert _status(requirement, supplier) is EvaluationStatus.UNKNOWN


def test_boolean_capability_four_states() -> None:
    required = _requirement(
        RequirementKind.CAPABILITY, {"capability_key": "CUSTOM_BRANDING", "value": True}
    )
    claim = "capability:custom branding"
    assert _status(required, _supplier(capabilities=(("CUSTOM_BRANDING", "true"),))) is EvaluationStatus.UNKNOWN
    assert _status(
        required,
        _supplier(
            capabilities=(("CUSTOM_BRANDING", "true"),),
            evidence=(_evidence(claim, "SUPPORTS"),),
        ),
    ) is EvaluationStatus.MEETS
    assert _status(
        required,
        _supplier(
            capabilities=(("CUSTOM_BRANDING", "false"),),
            evidence=(_evidence(claim, "CONTRADICTS"),),
        ),
    ) is EvaluationStatus.DOES_NOT_MEET
    assert _status(
        required,
        _supplier(
            evidence=(_evidence(claim, "SUPPORTS"), _evidence(claim, "CONTRADICTS"))
        ),
    ) is EvaluationStatus.CONFLICT

    prohibited = _requirement(
        RequirementKind.CAPABILITY, {"capability_key": "CUSTOM_BRANDING", "value": False}
    )
    assert _status(
        prohibited,
        _supplier(
            capabilities=(("CUSTOM_BRANDING", "true"),),
            evidence=(_evidence(claim, "SUPPORTS"),),
        ),
    ) is EvaluationStatus.DOES_NOT_MEET
    assert _status(
        prohibited,
        _supplier(
            capabilities=(("CUSTOM_BRANDING", "false"),),
            evidence=(_evidence(claim, "CONTRADICTS"),),
        ),
    ) is EvaluationStatus.MEETS


def test_false_boolean_capability_with_unsupported_positive_evidence_is_unknown() -> None:
    prohibited = _requirement(
        RequirementKind.CAPABILITY, {"capability_key": "CUSTOM_BRANDING", "value": False}
    )
    supplier = _supplier(evidence=(_evidence("capability:custom branding", "SUPPORTS"),))
    assert _status(prohibited, supplier) is EvaluationStatus.UNKNOWN


def test_categorical_capability_requires_matching_support() -> None:
    requirement = _requirement(
        RequirementKind.CAPABILITY,
        {"capability_key": "PRODUCT_CATEGORY", "value": "cosmetic travel bag"},
    )
    other_category = _supplier(
        capabilities=(("PRODUCT_CATEGORY", "home textile pouch"),),
        evidence=(_evidence("category:home textile pouch", "SUPPORTS"),),
    )
    assert _status(requirement, other_category) is EvaluationStatus.UNKNOWN
    assert _status(
        requirement,
        _supplier(
            capabilities=(("PRODUCT_CATEGORY", "cosmetic travel bag"),),
            evidence=(_evidence("category:cosmetic travel bag", "SUPPORTS"),),
        ),
    ) is EvaluationStatus.MEETS
    assert _status(
        requirement,
        _supplier(evidence=(_evidence("category:cosmetic travel bag", "CONTRADICTS"),)),
    ) is EvaluationStatus.DOES_NOT_MEET
    assert _status(
        requirement,
        _supplier(
            evidence=(
                _evidence("category:cosmetic travel bag", "SUPPORTS"),
                _evidence("category:cosmetic travel bag", "CONTRADICTS"),
            )
        ),
    ) is EvaluationStatus.CONFLICT


def test_categorical_method_uses_its_own_claim() -> None:
    requirement = _requirement(
        RequirementKind.CAPABILITY,
        {"capability_key": "BRANDING_METHOD", "value": "screen print"},
    )
    supplier = _supplier(
        capabilities=(("BRANDING_METHOD", "screen print"),),
        evidence=(_evidence("capability:custom branding", "SUPPORTS"),),
    )
    assert _status(requirement, supplier) is EvaluationStatus.UNKNOWN


def test_moq_four_states_and_derived_result() -> None:
    requirement = _requirement(RequirementKind.MOQ, {"quantity": 3000})
    evidence = _evidence("moq:general", "SUPPORTS")
    assert _status(requirement, _supplier(moq=1000)) is EvaluationStatus.UNKNOWN
    assert _status(requirement, _supplier(evidence=(evidence,))) is EvaluationStatus.UNKNOWN
    assert _status(requirement, _supplier(moq=1000, evidence=(evidence,))) is EvaluationStatus.MEETS
    assert _status(requirement, _supplier(moq=5000, evidence=(evidence,))) is EvaluationStatus.DOES_NOT_MEET
    assert _status(
        requirement,
        _supplier(moq=1000, evidence=(evidence, _evidence("moq:general", "CONTRADICTS"))),
    ) is EvaluationStatus.CONFLICT
    derived = evaluate_supplier([], requested_quantity=2000, supplier=_supplier(moq=1000, evidence=(evidence,)))
    assert derived.results[0].requirement_id is None
    assert derived.results[0].status is EvaluationStatus.MEETS


def test_explicit_moq_tightens_quantity_and_does_not_add_derived_duplicate() -> None:
    requirement = _requirement(RequirementKind.MOQ, {"quantity": 1500})
    supplier = _supplier(moq=1800, evidence=(_evidence("moq:general", "SUPPORTS"),))
    result = evaluate_supplier([requirement], requested_quantity=2000, supplier=supplier)
    assert len(result.results) == 1
    assert result.results[0].status is EvaluationStatus.DOES_NOT_MEET
    loose = _requirement(RequirementKind.MOQ, {"quantity": 5000})
    assert _status(loose, _supplier(moq=3000, evidence=(_evidence("moq:general", "SUPPORTS"),))) is EvaluationStatus.DOES_NOT_MEET


def test_evidence_ids_are_sorted_and_other_contexts_do_not_conflict() -> None:
    requirement = _requirement(RequirementKind.CERTIFICATION, {"value": "grs"})
    high = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    low = UUID("00000000-0000-0000-0000-000000000001")
    supplier = _supplier(
        capabilities=(("CERTIFICATION", "grs"),),
        evidence=(
            _evidence("certification:grs:current", "SUPPORTS", id=high),
            _evidence("certification:grs:expired", "CONTRADICTS"),
            _evidence("certification:grs:current", "SUPPORTS", id=low),
        ),
    )
    result = evaluate_supplier([requirement], requested_quantity=2000, supplier=supplier).results[0]
    assert result.status is EvaluationStatus.MEETS
    assert result.evidence_ids == (low, high)


def test_non_supplier_stage_requirements_remain_informational() -> None:
    requirement = _requirement(RequirementKind.UNIT_PRICE, {"amount": "5.00"})
    result = evaluate_supplier([requirement], requested_quantity=2000, supplier=_supplier())
    assert result.informational_requirement_ids == (requirement.id,)
    assert len(result.results) == 1
    assert result.results[0].kind is RequirementKind.MOQ


def _fixture_supplier(key: str) -> SupplierEvaluationFacts:
    record = next(item for item in load_fixture_data()["suppliers"] if item["key"] == key)
    return _supplier(
        capabilities=tuple((kind, value) for kind, value in record["capabilities"]),
        moq=record["general_moq"],
        evidence=tuple(
            _evidence(claim, state, id=fixture_id("evidence", f"{key}:{evidence_key}"))
            for claim, _, _, _, state, evidence_key in record["evidence"]
        ),
    )


def test_seeded_supplier_regressions() -> None:
    grs = _requirement(RequirementKind.CERTIFICATION, {"value": "grs"})
    cedar = evaluate_supplier([], requested_quantity=2000, supplier=_fixture_supplier("cedar-pack-co"))
    moss = evaluate_supplier([grs], requested_quantity=2000, supplier=_fixture_supplier("moss-thread-bags"))
    sunrise = evaluate_supplier([grs], requested_quantity=2000, supplier=_fixture_supplier("sunrise-textile-lab"))
    assert cedar.results[0].status is EvaluationStatus.DOES_NOT_MEET
    assert moss.results[0].status is EvaluationStatus.UNKNOWN
    assert sunrise.results[0].status is EvaluationStatus.CONFLICT
    assert sunrise.results[0].evidence_ids == tuple(sorted((
        fixture_id("evidence", "sunrise-textile-lab:grs-register-a"),
        fixture_id("evidence", "sunrise-textile-lab:grs-register-b"),
    ), key=str))
