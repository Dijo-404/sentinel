"""Prove each required stub case exists and fails closed where expected."""

import pytest
from stubs import (
    MalformedActionLedger,
    MalformedEvidence,
    MalformedIndicContext,
    MalformedPolicy,
    MalformedVerifier,
    UnauthorizedActionLedger,
    UnauthorizedEvidence,
    UnauthorizedIndicContext,
    UnauthorizedPolicy,
    UnauthorizedVerifier,
    UnavailableActionLedger,
    UnavailableEvidence,
    UnavailableIndicContext,
    UnavailablePolicy,
    UnavailableVerifier,
    ValidActionLedger,
    ValidEvidence,
    ValidIndicContext,
    ValidPolicy,
    ValidVerifier,
)
from stubs._payloads import DIGEST, REFUND_ACTION

from sentinel_finharness import ContractViolation, FinHarnessClient, PeerError, RuntimeConfig


def _enabled(manifest):
    return RuntimeConfig.from_mapping(
        {
            "enabled": True,
            "execution_mode": "harness",
            "financial_writes": True,
            "allowed_workflows": [manifest.workflow_name],
            "allowed_tenants": ["sandbox"],
        }
    )


def _client(manifest, **peers):
    defaults = {
        "evidence": ValidEvidence(),
        "policy": ValidPolicy(),
        "ledger": ValidActionLedger(),
        "verifier": ValidVerifier(),
        "indic_context": ValidIndicContext(),
    }
    defaults.update(peers)
    return FinHarnessClient(
        config=_enabled(manifest),
        manifest=manifest,
        tenant_id="sandbox",
        **defaults,
    )


@pytest.mark.parametrize(
    "peer_kw, method, args, expect",
    [
        (
            {"evidence": UnavailableEvidence()},
            "collect_evidence",
            {"case_id": "case-demo-42", "case_revision": 1, "order_reference": "DEMO-ORDER-42"},
            ("evidence.v1", "unavailable"),
        ),
        (
            {"evidence": UnauthorizedEvidence()},
            "collect_evidence",
            {"case_id": "case-demo-42", "case_revision": 1, "order_reference": "DEMO-ORDER-42"},
            ("evidence.v1", "unauthorized_or_out_of_scope"),
        ),
        (
            {"policy": UnavailablePolicy()},
            "evaluate_policy",
            {"payload": REFUND_ACTION, "evidence": []},
            ("policy.v1", "unavailable"),
        ),
        (
            {"policy": UnauthorizedPolicy()},
            "evaluate_policy",
            {"payload": REFUND_ACTION, "evidence": []},
            ("policy.v1", "unauthorized_or_out_of_scope"),
        ),
        (
            {"ledger": UnavailableActionLedger()},
            "create_proposal",
            {
                "operation_key": "k",
                "payload": REFUND_ACTION,
                "action_digest": DIGEST,
            },
            ("action-ledger.v1", "unavailable"),
        ),
        (
            {"ledger": UnauthorizedActionLedger()},
            "create_proposal",
            {
                "operation_key": "k",
                "payload": REFUND_ACTION,
                "action_digest": DIGEST,
            },
            ("action-ledger.v1", "unauthorized_or_out_of_scope"),
        ),
        (
            {"verifier": UnavailableVerifier()},
            "assess",
            {
                "case_id": "case-demo-42",
                "case_revision": 1,
                "action_id": "action-demo-1",
                "provider_ref": "refund-demo-1",
            },
            ("verifier.v1", "unavailable"),
        ),
        (
            {"verifier": UnauthorizedVerifier()},
            "assess",
            {
                "case_id": "case-demo-42",
                "case_revision": 1,
                "action_id": "action-demo-1",
                "provider_ref": "refund-demo-1",
            },
            ("verifier.v1", "unauthorized_or_out_of_scope"),
        ),
        (
            {"indic_context": UnavailableIndicContext()},
            "propose",
            {
                "case": {
                    "contract_version": "sentinel.task-contracts.v1",
                    "case_id": "case-demo-42",
                    "revision": 1,
                    "status": "RECEIVED",
                    "language": "en-IN",
                    "intent": "duplicate_payment",
                    "evidence_ids": [],
                },
                "input": {
                    "case_id": "case-demo-42",
                    "case_revision": 1,
                    "original_text": "x",
                    "language": "en-IN",
                    "order_reference": "DEMO-ORDER-42",
                    "messages": [],
                },
                "evidence": [],
            },
            ("indic-context.v1", "unavailable"),
        ),
        (
            {"indic_context": UnauthorizedIndicContext()},
            "propose",
            {
                "case": {
                    "contract_version": "sentinel.task-contracts.v1",
                    "case_id": "case-demo-42",
                    "revision": 1,
                    "status": "RECEIVED",
                    "language": "en-IN",
                    "intent": "duplicate_payment",
                    "evidence_ids": [],
                },
                "input": {
                    "case_id": "case-demo-42",
                    "case_revision": 1,
                    "original_text": "x",
                    "language": "en-IN",
                    "order_reference": "DEMO-ORDER-42",
                    "messages": [],
                },
                "evidence": [],
            },
            ("indic-context.v1", "unauthorized_or_out_of_scope"),
        ),
    ],
)
def test_stub_peer_errors(manifest, peer_kw, method, args, expect):
    client = _client(manifest, **peer_kw)
    with pytest.raises(PeerError) as exc:
        getattr(client, method)(args)
    assert (exc.value.peer, exc.value.code) == expect


@pytest.mark.parametrize(
    "peer_kw, method, args",
    [
        (
            {"evidence": MalformedEvidence()},
            "collect_evidence",
            {"case_id": "case-demo-42", "case_revision": 1, "order_reference": "DEMO-ORDER-42"},
        ),
        (
            {"policy": MalformedPolicy()},
            "evaluate_policy",
            {"payload": REFUND_ACTION, "evidence": []},
        ),
        (
            {"ledger": MalformedActionLedger()},
            "create_proposal",
            {
                "operation_key": "k",
                "payload": REFUND_ACTION,
                "action_digest": DIGEST,
            },
        ),
        (
            {"verifier": MalformedVerifier()},
            "assess",
            {
                "case_id": "case-demo-42",
                "case_revision": 1,
                "action_id": "action-demo-1",
                "provider_ref": "refund-demo-1",
            },
        ),
        (
            {"indic_context": MalformedIndicContext()},
            "propose",
            {
                "case": {
                    "contract_version": "sentinel.task-contracts.v1",
                    "case_id": "case-demo-42",
                    "revision": 1,
                    "status": "RECEIVED",
                    "language": "en-IN",
                    "intent": "duplicate_payment",
                    "evidence_ids": [],
                },
                "input": {
                    "case_id": "case-demo-42",
                    "case_revision": 1,
                    "original_text": "x",
                    "language": "en-IN",
                    "order_reference": "DEMO-ORDER-42",
                    "messages": [],
                },
                "evidence": [],
            },
        ),
    ],
)
def test_stub_malformed_rejected(manifest, peer_kw, method, args):
    client = _client(manifest, **peer_kw)
    with pytest.raises(ContractViolation):
        getattr(client, method)(args)


def test_valid_stubs_roundtrip(manifest):
    client = _client(manifest)
    bundle = client.collect_evidence(
        {
            "case_id": "case-demo-42",
            "case_revision": 1,
            "order_reference": "DEMO-ORDER-42",
        }
    )
    assert bundle["contract_version"] == "sentinel.task-contracts.v1"
    model = client.propose(
        {
            "case": {
                "contract_version": "sentinel.task-contracts.v1",
                "case_id": "case-demo-42",
                "revision": 1,
                "status": "RECEIVED",
                "language": "en-IN",
                "intent": "duplicate_payment",
                "evidence_ids": [],
            },
            "input": {
                "case_id": "case-demo-42",
                "case_revision": 1,
                "original_text": "x",
                "language": "en-IN",
                "order_reference": "DEMO-ORDER-42",
                "messages": [],
            },
            "evidence": [],
        }
    )
    assert model["outcome"] == "PROPOSAL"
    policy = client.evaluate_policy({"payload": REFUND_ACTION, "evidence": []})
    assert policy["outcome"] == "REQUIRE_APPROVAL"
    record = client.create_proposal(
        {
            "operation_key": "k",
            "payload": REFUND_ACTION,
            "action_digest": DIGEST,
        }
    )
    assert record["status"] == "PROPOSED"
    reserved = client.reserve(
        {
            "operation_key": "k",
            "payload": REFUND_ACTION,
            "action_digest": DIGEST,
            "approval_id": "synthetic-approval_id",
        }
    )
    assert reserved["status"] == "RESERVED"
    assessment = client.assess(
        {
            "case_id": "case-demo-42",
            "case_revision": 1,
            "action_id": reserved["action_id"],
            "provider_ref": reserved["provider_ref"],
        }
    )
    assert assessment["status"] == "WAITING"
