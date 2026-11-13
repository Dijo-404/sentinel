"""Stub behaviors for case-api.v1: valid / unavailable / malformed / unauthorized."""

from __future__ import annotations

import pytest
from tests.stubs import malformed, unauthorized_or_out_of_scope, unavailable, valid

from sentinel_merchant_sla.application.errors import (
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_merchant_sla.contracts import Principal

PRINCIPAL = Principal(
    principal_id="op",
    tenant_id="demo-tenant-a",
    roles=("operator",),
    subject_refs=("*",),
    case_ids=("*",),
    merchant_refs=("*",),
)


def test_valid_stub_returns_case():
    case = valid().get_case("case-demo-42", PRINCIPAL)
    assert case.case_id == "case-demo-42"
    assert case.status == "INVESTIGATING"


def test_unavailable_stub_fails_closed():
    with pytest.raises(PeerUnavailableError):
        unavailable().get_case("case-demo-42", PRINCIPAL)


def test_malformed_stub_fails_closed():
    with pytest.raises(PeerMalformedError):
        malformed().get_case("case-demo-42", PRINCIPAL)


def test_unauthorized_stub_fails_closed():
    with pytest.raises(PeerUnauthorizedError):
        unauthorized_or_out_of_scope().get_case("case-demo-42", PRINCIPAL)


def test_valid_escalate_never_verified_resolved():
    peer = valid()
    case = peer.escalate_case(
        "case-demo-42",
        expected_revision=1,
        reason_code="SLA_BREACH",
        owner_queue="merchant-ops",
        principal=PRINCIPAL,
    )
    assert case.status == "ESCALATED"
    assert case.status != "VERIFIED_RESOLVED"
