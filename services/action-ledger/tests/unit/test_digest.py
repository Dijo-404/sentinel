"""Canonical digest fixtures must match the pinned contract vector."""

from __future__ import annotations

import json
from pathlib import Path

from sentinel_action_ledger.domain.digest import action_digest, canonical_bytes

ROOT = Path(__file__).resolve().parents[2]
VECTOR = json.loads((ROOT / "contracts/canonical-digest.json").read_text())
PAYLOAD = {
    "action": "REQUEST_REFUND",
    "case_id": "case-demo-42",
    "case_revision": 1,
    "transaction_ref": "TXN-B",
    "amount_minor": 150000,
    "currency": "INR",
    "destination": "ORIGINAL_PAYMENT_ROUTE",
    "evidence_ids": ["evidence-payment-b", "evidence-order"],
    "policy_version": "demo-policy-v1",
}


def test_canonical_bytes_match_contract_vector():
    assert canonical_bytes(PAYLOAD).decode("utf-8") == VECTOR["canonical_action_utf8"]
    assert action_digest(PAYLOAD) == VECTOR["expected_sha256"]


def test_rejects_undeclared_fields():
    bad = {**PAYLOAD, "extra": "nope"}
    try:
        action_digest(bad)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "Undeclared" in str(exc)
