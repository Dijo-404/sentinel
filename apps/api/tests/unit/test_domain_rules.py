"""Domain rule unit tests."""

from datetime import UTC, datetime

import pytest

from sentinel_api.adapters.peers.fixture_clients import sample_verified_assessment
from sentinel_api.domain.rules import (
    assert_verified_resolution,
    order_bound_to_subject,
    require_order_bound_to_principal,
    validate_result,
)
from sentinel_api.domain.types import CaseResult, DomainError


def test_order_bound_to_subject_equal_or_prefixed():
    assert order_bound_to_subject("subject-a", "subject-a")
    assert order_bound_to_subject("subject-a/DEMO-ORDER-42", "subject-a")
    assert order_bound_to_subject("subject-a:42", "subject-a")
    assert not order_bound_to_subject("subject-ab", "subject-a")
    assert not order_bound_to_subject("DEMO-ORDER-42", "subject-a")
    assert not order_bound_to_subject("subject-b/ORDER", "subject-a")


def test_require_order_bound_fail_closed():
    require_order_bound_to_principal("subject-a/ORDER", subject_refs=("subject-a",), enforce=True)
    require_order_bound_to_principal("any-order", subject_refs=(), enforce=False)
    with pytest.raises(DomainError) as empty:
        require_order_bound_to_principal("subject-a/ORDER", subject_refs=(), enforce=True)
    assert empty.value.code == "FORBIDDEN"
    with pytest.raises(DomainError) as victim:
        require_order_bound_to_principal(
            "subject-b/VICTIM", subject_refs=("subject-a",), enforce=True
        )
    assert victim.value.code == "FORBIDDEN"


def test_verified_resolved_requires_assessment_id():
    with pytest.raises(DomainError) as exc:
        validate_result(
            {
                "event_key": "k1",
                "expected_revision": 1,
                "status": "VERIFIED_RESOLVED",
                "evidence_ids": ["e1"],
                "reason_code": "DONE",
            }
        )
    assert exc.value.code == "INVALID_INPUT"


def test_assessment_must_match_case_action_revision():
    result = CaseResult(
        event_key="k1",
        expected_revision=2,
        status="VERIFIED_RESOLVED",
        evidence_ids=("e1",),
        reason_code="DONE",
        action_id="action-1",
        assessment_id="assess-1",
    )
    assessment = sample_verified_assessment(
        assessment_id="assess-1",
        case_id="case-1",
        case_revision=1,
        action_id="action-1",
    )
    with pytest.raises(DomainError) as exc:
        assert_verified_resolution(
            result=result,
            case_id="case-1",
            assessment=assessment,
            now=datetime(2026, 11, 13, tzinfo=UTC),
        )
    assert exc.value.code == "ASSESSMENT_MISMATCH"
