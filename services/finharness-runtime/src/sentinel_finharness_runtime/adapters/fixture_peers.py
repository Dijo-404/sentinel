"""In-package fixture peers for CLI self-check. Labeled fixture — not product evidence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sentinel_finharness_runtime.domain.models import CONTRACT_VERSION

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


class FixtureEvidence:
    def collect(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        return dict(EVIDENCE_BUNDLE)


class FixturePolicy:
    def evaluate(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        return dict(POLICY_RESULT)


class FixtureIndicContext:
    def propose(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        result = dict(MODEL_RESULT)
        result["original_text"] = request["input"]["original_text"]
        result["language"] = request["input"]["language"]
        return result


class FixtureLedger:
    def create_proposal(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        return dict(ACTION_RECORD)

    def reserve(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        record = dict(ACTION_RECORD)
        record["status"] = "RESERVED"
        return record

    def get_action(self, action_id: str) -> Mapping[str, Any]:
        record = dict(ACTION_RECORD)
        record["action_id"] = action_id
        return record

    def query_by_provider_ref(self, provider_ref: str) -> Mapping[str, Any]:
        return {
            "action_id": "action-demo-1",
            "provider_ref": provider_ref,
            "status": "SUBMITTED",
            "payload": REFUND_ACTION,
            "action_digest": DIGEST,
        }


class FixtureVerifier:
    def assess(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "assessment_id": "synthetic-assessment_id",
            "case_id": request["case_id"],
            "case_revision": request["case_revision"],
            "action_id": request["action_id"],
            "assessed_at": "2026-11-13T12:00:00Z",
            "expires_at": "2026-11-13T13:00:00Z",
            "status": "WAITING",
            "evidence": [],
            "reason_codes": ["awaiting-provider-credit"],
        }
