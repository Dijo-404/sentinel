"""Synthetic wire payloads labeled fixture. Not live financial evidence."""

from __future__ import annotations

CONTRACT_VERSION = "sentinel.task-contracts.v1"
DIGEST = "d5ce68ac9b173525d7ed0989eeb374cbb41b0a551f4457f8406d85342e1a8993"

REFUND_ACTION = {
    "case_id": "case-demo-42",
    "case_revision": 1,
    "evidence_ids": ["evidence-payment-b", "evidence-order"],
    "policy_version": "demo-policy-v1",
    "action": "REQUEST_REFUND",
    "transaction_ref": "TXN-B",
    "amount_minor": 150000,
    "currency": "INR",
    "destination": "ORIGINAL_PAYMENT_ROUTE",
}

EVIDENCE_BUNDLE = {
    "contract_version": CONTRACT_VERSION,
    "case_id": "case-demo-42",
    "evidence": [
        {
            "evidence_id": "evidence-payment-b",
            "case_id": "case-demo-42",
            "source": "fixture",
            "subject_ref": "subject-demo",
            "observed_at": "2026-11-13T12:00:00Z",
            "expires_at": "2026-11-13T13:00:00Z",
            "digest": DIGEST,
            "verification_status": "VERIFIED",
            "facts": {
                "kind": "PAYMENT",
                "payment": {
                    "transaction_ref": "TXN-B",
                    "order_reference": "DEMO-ORDER-42",
                    "subject_ref": "subject-demo",
                    "status": "CAPTURED",
                    "amount_minor": 150000,
                    "currency": "INR",
                },
            },
        }
    ],
    "reconciliation_codes": ["fixture-duplicate-candidate"],
}

POLICY_RESULT = {
    "outcome": "REQUIRE_APPROVAL",
    "reason_codes": ["refund-requires-supervisor"],
    "policy_version": "demo-policy-v1",
    "action_digest": DIGEST,
    "required_evidence": [],
}

MODEL_RESULT = {
    "outcome": "PROPOSAL",
    "reason_codes": [],
    "original_text": "Synthetic duplicate payment complaint",
    "language": "en-IN",
    "proposal": REFUND_ACTION,
}

ACTION_RECORD = {
    "action_id": "action-demo-1",
    "provider_ref": "refund-demo-1",
    "payload": REFUND_ACTION,
    "action_digest": DIGEST,
    "status": "PROPOSED",
}

RESERVED_RECORD = {
    **ACTION_RECORD,
    "status": "RESERVED",
    "approval": {
        "approval_id": "synthetic-approval_id",
        "action_digest": DIGEST,
        "case_revision": 1,
        "policy_version": "demo-policy-v1",
        "decision": "APPROVE",
        "reviewer_id": "synthetic-reviewer_id",
        "expires_at": "2026-11-13T13:00:00Z",
    },
}

VERIFICATION_RESULT = {
    "assessment_id": "synthetic-assessment_id",
    "case_id": "case-demo-42",
    "case_revision": 1,
    "action_id": "action-demo-1",
    "assessed_at": "2026-11-13T12:00:00Z",
    "expires_at": "2026-11-13T13:00:00Z",
    "status": "WAITING",
    "evidence": [],
    "reason_codes": ["awaiting-provider-credit"],
}

SDK_READ_RESULT = {
    "contract_version": CONTRACT_VERSION,
    "outcome": "PROPOSAL",
    "proposal": REFUND_ACTION,
    "reason_codes": [],
}
