from copy import deepcopy

import pytest

from sourcepilot.ai.supplier_explanation_eval import load_cases, score_case


def test_supplier_explanation_groundedness_cases() -> None:
    cases = load_cases()
    assert len(cases) == 11
    assert len({case["id"] for case in cases}) == len(cases)
    for case in cases:
        assert score_case(case) is case["expected_valid"], case["id"]


@pytest.mark.parametrize("section,status,importance", [
    ("strengths", "MEETS", "REQUIRED"),
    ("required_failures", "DOES_NOT_MEET", "REQUIRED"),
    ("preferred_findings", "MEETS", "PREFERRED"),
    ("preferred_findings", "DOES_NOT_MEET", "PREFERRED"),
    ("unknowns", "UNKNOWN", "REQUIRED"),
    ("conflicts", "CONFLICT", "PREFERRED"),
    ("concerns", "DOES_NOT_MEET", "REQUIRED"),
])
def test_requirement_points_need_attached_evidence_when_available(
    section: str, status: str, importance: str,
) -> None:
    requirement_id = "22222222-2222-2222-2222-222222222221"
    evidence_id = "33333333-3333-3333-3333-333333333331"
    point = {"text": None, "requirement_id": requirement_id, "evidence_ids": [evidence_id]}
    case = {
        "findings": [{
            "requirement_id": requirement_id, "kind": "MATERIAL",
            "importance": importance, "expected_value": {"value": "recycled polyester"},
            "status": status, "evidence_ids": [evidence_id],
        }],
        "fetched_evidence_ids": [evidence_id],
        "output": {
            "supplier_id": "11111111-1111-1111-1111-111111111111",
            "strengths": [], "required_failures": [], "preferred_findings": [],
            "unknowns": [], "conflicts": [], "concerns": [], "evidence_ids": [evidence_id],
        },
    }
    # Required failures, unknowns and conflicts must still appear in their own sections.
    required_section = {
        "DOES_NOT_MEET": "required_failures" if importance == "REQUIRED" else None,
        "UNKNOWN": "unknowns", "CONFLICT": "conflicts",
    }.get(status)
    case["output"][section].append(point)
    if required_section and required_section != section:
        case["output"][required_section].append(deepcopy(point))
    assert score_case(case)

    missing = deepcopy(case)
    missing["output"][section][0]["evidence_ids"] = []
    assert not score_case(missing)

    contradictory = deepcopy(case)
    contradictory["output"][section][0]["text"] = {
        "MEETS": "This requirement does not meet the brief.",
        "DOES_NOT_MEET": "This requirement meets the brief.",
        "UNKNOWN": "This requirement meets the brief.",
        "CONFLICT": "There is no conflict for this requirement.",
    }[status]
    assert not score_case(contradictory)

    no_evidence = deepcopy(case)
    no_evidence["findings"][0]["evidence_ids"] = []
    no_evidence["fetched_evidence_ids"] = []
    no_evidence["output"]["evidence_ids"] = []
    for points in no_evidence["output"].values():
        if isinstance(points, list):
            for item in points:
                if isinstance(item, dict):
                    item["evidence_ids"] = []
    assert score_case(no_evidence)


def test_evidence_only_concern_keeps_supported_text() -> None:
    case = {
        "findings": [],
        "fetched_evidence_ids": ["33333333-3333-3333-3333-333333333331"],
        "output": {
            "supplier_id": "11111111-1111-1111-1111-111111111111",
            "strengths": [], "required_failures": [], "preferred_findings": [],
            "unknowns": [], "conflicts": [],
            "concerns": [{
                "text": "Indicative pricing needs review.", "requirement_id": None,
                "evidence_ids": ["33333333-3333-3333-3333-333333333331"],
            }],
            "evidence_ids": ["33333333-3333-3333-3333-333333333331"],
        },
    }
    assert score_case(case)
