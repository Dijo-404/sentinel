"""Stub mode matrix for all four consumed ports."""

from __future__ import annotations

import pytest
from tests.stubs import StubCaseApi, StubEvidence, StubLedger, StubPolicy

from sentinel_merchant_refunds.domain.errors import PeerError
from sentinel_merchant_refunds.domain.types import Principal, ProposalRequest

MODES = ["unavailable", "malformed", "unauthorized_or_out_of_scope"]
PRINCIPAL = Principal(
    principal_id="p",
    tenant_id="tenant-demo-1",
    merchant_ref="merchant-demo-1",
    roles=["merchant_staff"],
)


@pytest.mark.parametrize("mode", MODES)
def test_case_api_stub_modes(mode):
    stub = StubCaseApi(mode=mode)  # type: ignore[arg-type]
    with pytest.raises(PeerError):
        stub.get_case(PRINCIPAL, "case-demo-42")


@pytest.mark.parametrize("mode", MODES)
def test_evidence_stub_modes(mode):
    stub = StubEvidence(mode=mode)  # type: ignore[arg-type]
    with pytest.raises(PeerError):
        stub.get_case_evidence(PRINCIPAL, "case-demo-42")


@pytest.mark.parametrize("mode", MODES)
def test_policy_stub_modes(mode):
    stub = StubPolicy(mode=mode)  # type: ignore[arg-type]
    with pytest.raises(PeerError):
        stub.evaluate(PRINCIPAL, payload={"action": "REQUEST_REFUND"}, evidence_ids=["e1"])


@pytest.mark.parametrize("mode", MODES)
def test_ledger_stub_modes(mode):
    stub = StubLedger(mode=mode)  # type: ignore[arg-type]
    with pytest.raises(PeerError):
        stub.create_proposal(
            PRINCIPAL,
            ProposalRequest(operation_key="k", payload={}, action_digest="d"),
        )
