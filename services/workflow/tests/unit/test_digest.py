from pathlib import Path

from sentinel_workflow.domain.digest import action_digest, canonical_action_bytes


def test_canonical_digest_matches_baseline_fixture():
    import json

    fixture = json.loads(
        (Path(__file__).resolve().parents[2] / "contracts" / "canonical_digest.json").read_text()
    )
    payload = {
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
    assert canonical_action_bytes(payload).decode() == fixture["canonical_action_utf8"]
    assert action_digest(payload) == fixture["expected_sha256"]
