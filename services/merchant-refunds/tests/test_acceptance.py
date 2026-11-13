"""Acceptance: happy path uses ledger/policy only; failures leave no forged action_id."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from tests.stubs import StubCaseApi, StubEvidence, StubLedger, StubPolicy

from sentinel_merchant_refunds.adapters.clock import FixedClock
from sentinel_merchant_refunds.adapters.ids import SecureIdGenerator
from sentinel_merchant_refunds.adapters.memory_store import MemoryRequestStore
from sentinel_merchant_refunds.application.service import MerchantRefundService
from sentinel_merchant_refunds.domain.errors import PeerError
from sentinel_merchant_refunds.domain.types import ApprovalDecision, DraftCreate, Principal

SRC_ROOT = Path(__file__).resolve().parents[1] / "src" / "sentinel_merchant_refunds"


def _service(case_api, evidence, policy, ledger) -> MerchantRefundService:
    return MerchantRefundService(
        store=MemoryRequestStore(),
        case_api=case_api,
        evidence=evidence,
        policy=policy,
        ledger=ledger,
        clock=FixedClock("2026-11-13T12:00:00Z"),
        ids=SecureIdGenerator(),
    )


def _principal() -> Principal:
    return Principal(
        principal_id="staff-demo-1",
        tenant_id="tenant-demo-1",
        merchant_ref="merchant-demo-1",
        roles=["merchant_staff"],
    )


def _draft(**overrides) -> DraftCreate:
    body = {
        "case_id": "case-demo-42",
        "transaction_ref": "TXN-B",
        "amount_minor": 150000,
        "currency": "INR",
        "evidence_ids": ["evidence-payment-b", "evidence-order"],
        "rationale": "Duplicate capture",
    }
    body.update(overrides)
    return DraftCreate.model_validate(body)


def test_happy_path_awaiting_approval_then_reserved_via_ledger_policy_only():
    case_api = StubCaseApi()
    evidence = StubEvidence()
    evidence.seed_demo()
    policy = StubPolicy()
    ledger = StubLedger()
    svc = _service(case_api, evidence, policy, ledger)
    principal = _principal()

    draft = svc.create_draft(principal, _draft(), idempotency_key="k1")
    assert draft.status == "DRAFT"
    assert draft.action_id is None

    awaiting = svc.submit(principal, draft.request_id)
    assert awaiting.status == "AWAITING_APPROVAL"
    assert awaiting.action_id == "action-ledger-1"
    assert awaiting.action_id in ledger.forged_action_ids()
    assert policy.calls == 1
    assert ledger.proposal_calls == 1
    assert ledger.reserve_calls == 0
    assert case_api.calls == 1
    assert evidence.calls == 1

    decision = ApprovalDecision(
        decision="APPROVE",
        approval_id="approval-demo-1",
        action_digest=awaiting.action_digest or "",
        case_revision=1,
        policy_version="demo-policy-v1",
        expires_at="2026-11-13T18:00:00Z",
        reviewer_id="supervisor-demo-1",
    )
    reserved = svc.apply_decision(principal, draft.request_id, decision)
    assert reserved.status == "RESERVED"
    assert reserved.action_id == "action-ledger-1"
    assert reserved.approval_id == "approval-demo-1"
    assert reserved.credit_verified() is False
    assert ledger.reserve_calls == 1


def test_policy_deny_leaves_no_action_id():
    policy = StubPolicy(outcome="DENY")
    ledger = StubLedger()
    evidence = StubEvidence()
    evidence.seed_demo()
    svc = _service(StubCaseApi(), evidence, policy, ledger)
    principal = _principal()
    draft = svc.create_draft(principal, _draft(), idempotency_key="deny-1")
    rejected = svc.submit(principal, draft.request_id)
    assert rejected.status == "REJECTED"
    assert rejected.action_id is None
    assert ledger.proposal_calls == 0
    assert ledger.forged_action_ids() == set()


def _unavailable_peers(which: str):
    case_api = StubCaseApi(mode="unavailable" if which == "case_api" else "valid")
    evidence = StubEvidence(mode="unavailable" if which == "evidence" else "valid")
    policy = StubPolicy(mode="unavailable" if which == "policy" else "valid")
    ledger = StubLedger(mode="unavailable" if which == "ledger" else "valid")
    if which != "evidence":
        evidence.seed_demo()
    return case_api, evidence, policy, ledger


@pytest.mark.parametrize("peer_name", ["case_api", "evidence", "policy", "ledger"])
def test_peer_failure_leaves_no_forged_action_id(peer_name):
    case_api, evidence, policy, ledger = _unavailable_peers(peer_name)
    svc = _service(case_api, evidence, policy, ledger)
    principal = _principal()
    draft = svc.create_draft(principal, _draft(), idempotency_key=f"fail-{peer_name}")
    with pytest.raises(PeerError):
        svc.submit(principal, draft.request_id)
    stored = svc.store.get(principal.tenant_id, draft.request_id)
    assert stored is not None
    assert stored.action_id is None
    assert ledger.forged_action_ids() == set() or ledger.proposal_calls == 0


def test_http_happy_path(client, auth_headers, draft_body):
    create = client.post("/v1/refund-requests", json=draft_body, headers=auth_headers)
    assert create.status_code == 201
    request_id = create.json()["request_id"]
    assert create.json()["status"] == "DRAFT"
    assert create.json()["credit_verified"] is False

    submit = client.post(f"/v1/refund-requests/{request_id}/submit", headers=auth_headers)
    assert submit.status_code == 200
    body = submit.json()
    assert body["status"] == "AWAITING_APPROVAL"
    assert body["action_id"].startswith("action-ledger-")
    assert body["credit_verified"] is False
    assert body["action_digest"]

    decide = client.post(
        f"/v1/refund-requests/{request_id}/decisions",
        headers=auth_headers,
        json={
            "decision": "APPROVE",
            "approval_id": "approval-demo-1",
            "action_digest": body["action_digest"],
            "case_revision": 1,
            "policy_version": "demo-policy-v1",
            "expires_at": "2026-11-13T18:00:00Z",
            "reviewer_id": "supervisor-demo-1",
        },
    )
    assert decide.status_code == 200
    reserved = decide.json()
    assert reserved["status"] == "RESERVED"
    assert reserved["action_id"] == body["action_id"]
    assert reserved["credit_verified"] is False

    sync = client.post(f"/v1/refund-requests/{request_id}/sync", headers=auth_headers)
    assert sync.status_code == 200
    assert sync.json()["status"] == "RESERVED"
    assert sync.json()["credit_verified"] is False


def test_no_payment_provider_write_adapter_in_source():
    forbidden = (
        "payment.provider",
        "PaymentProvider",
        "mint_refund",
        "payment_provider",
        "ProviderWrite",
    )
    for path in SRC_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{path} contains {needle}"
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "simulator" not in alias.name
                    assert "payment_provider" not in alias.name
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "simulator" not in node.module
                assert "payment_provider" not in node.module
                assert "dispatcher" not in node.module


def test_capabilities_and_health(client):
    assert client.get("/healthz").json()["status"] == "ok"
    ready = client.get("/readyz").json()
    assert ready["mode"] == "fixture"
    caps = client.get("/v1/capabilities").json()
    assert caps["port"] == "merchant-refunds.v1"
    assert caps["contract_sha256"].startswith("0db3ba2b")
