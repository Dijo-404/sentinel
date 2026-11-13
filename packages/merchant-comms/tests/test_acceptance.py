"""Acceptance: approval gate, reject not sent, indic fallback labeled, unauthorized fail closed."""

from __future__ import annotations

import pytest

from sentinel_merchant_comms.application.errors import (
    ConflictError,
    ForbiddenError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_merchant_comms.domain.templates import FAKE_LABEL
from sentinel_merchant_comms.domain.types import CONTRACT_SHA256, PORT, Principal
from tests.stubs.case_api import UnauthorizedCaseApi, UnavailableCaseApi
from tests.stubs.indic_context import UnavailableIndicContext


def test_contract_hash_pinned() -> None:
    assert CONTRACT_SHA256 == ("0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb")
    assert PORT == "merchant-comms.v1"


def test_approval_required_before_simulated_send(service_factory, operator) -> None:
    service = service_factory()
    draft = service.create_draft(case_id="case-demo-42", language="en", principal=operator)
    assert draft.status == "DRAFT"
    assert draft.delivery_history == []

    with pytest.raises(ConflictError) as exc:
        service.simulate_send(draft_id=draft.draft_id, principal=operator)
    assert exc.value.code == "APPROVAL_REQUIRED"

    approved = service.decide(draft_id=draft.draft_id, decision="APPROVE", principal=operator)
    assert approved.status == "APPROVED"

    sent = service.simulate_send(draft_id=approved.draft_id, principal=operator)
    assert sent.status == "SIMULATED_SENT"
    assert len(sent.delivery_history) == 1
    assert sent.delivery_history[0].status == "SIMULATED_SENT"
    assert sent.delivery_history[0].channel == "merchant-portal"
    assert sent.delivery_history[0].at == "2026-11-13T19:30:00Z"


def test_rejected_draft_not_delivered(service_factory, operator) -> None:
    service = service_factory()
    draft = service.create_draft(case_id="case-demo-42", language="ta", principal=operator)
    rejected = service.decide(draft_id=draft.draft_id, decision="REJECT", principal=operator)
    assert rejected.status == "REJECTED"
    assert rejected.delivery_history == []

    with pytest.raises(ConflictError) as exc:
        service.simulate_send(draft_id=rejected.draft_id, principal=operator)
    assert exc.value.code == "DRAFT_REJECTED"
    assert service.get_draft(rejected.draft_id, operator).delivery_history == []


def test_missing_indic_falls_back_to_labeled_fake(service_factory, operator) -> None:
    service = service_factory(use_indic=False)
    draft = service.create_draft(case_id="case-demo-42", language="hi", principal=operator)
    assert draft.status == "DRAFT"
    assert FAKE_LABEL in draft.body
    assert "case-demo-42" in draft.body


def test_unavailable_indic_falls_back_to_labeled_fake(service_factory, operator) -> None:
    service = service_factory(indic=UnavailableIndicContext())
    draft = service.create_draft(case_id="case-demo-42", language="en", principal=operator)
    assert FAKE_LABEL in draft.body
    assert draft.status == "DRAFT"


def test_unauthorized_case_scope_fails_closed(service_factory, operator) -> None:
    service = service_factory(case_api=UnauthorizedCaseApi())
    with pytest.raises(PeerUnauthorizedError):
        service.create_draft(case_id="case-demo-42", language="en", principal=operator)


def test_unavailable_case_api_fails_closed(service_factory, operator) -> None:
    service = service_factory(case_api=UnavailableCaseApi())
    with pytest.raises(PeerUnavailableError):
        service.create_draft(case_id="case-demo-42", language="en", principal=operator)


def test_principal_out_of_scope_fails_closed(service_factory) -> None:
    service = service_factory()
    outsider = Principal(
        principal_id="op-other",
        tenant_id="tenant-demo",
        roles=["operator"],
        subject_refs=["subject-demo"],
        case_ids=["case-other"],
    )
    with pytest.raises(ForbiddenError):
        service.create_draft(case_id="case-demo-42", language="en", principal=outsider)


def test_languages_en_ta_hi(service_factory, operator) -> None:
    service = service_factory(use_indic=False)
    for lang in ("en", "ta", "hi"):
        draft = service.create_draft(case_id="case-demo-42", language=lang, principal=operator)
        assert draft.language == lang
        assert FAKE_LABEL in draft.body
