from __future__ import annotations

from sentinel_replay.domain.models import FixtureEvent, ReplayFixture

CONTRACT_HASH = "0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb"
CONTRACT_VERSION = "sentinel.task-contracts.v1"

BUNDLED_FIXTURE_ID = "dup_refund_timeout_001"


def bundled_timeout_fixture() -> ReplayFixture:
    """Hero timeout/retry fixture with versions and seed (p1 §8.3 / §8.5)."""
    return ReplayFixture(
        fixture_id=BUNDLED_FIXTURE_ID,
        scenario="duplicate_captured_payment",
        seed=42,
        policy_version="demo-policy-v1",
        workflow_version="demo-workflow-v1",
        model_version="fake-model-v0",
        events=(
            FixtureEvent(at_s=2, type="merchant_confirms_duplicate"),
            FixtureEvent(at_s=5, type="reviewer_approves"),
            FixtureEvent(at_s=6, type="refund_accepted_response_timeout"),
            FixtureEvent(at_s=12, type="refund_provider_success"),
            FixtureEvent(at_s=15, type="synthetic_credit_confirmed"),
        ),
        expected={
            "terminal_state": "VERIFIED_RESOLVED",
            "refund_side_effect_count": 1,
            "refunded_minor": 150000,
            "approval_required": True,
            "unsafe_actions": 0,
        },
        refund={
            "action_id": "action-demo-1",
            "provider_ref": "refund-demo-1",
            "transaction_ref": "TXN-B",
            "amount_minor": 150000,
            "currency": "INR",
            "destination": "ORIGINAL_PAYMENT_ROUTE",
        },
    )


def fixture_by_id(fixture_id: str) -> ReplayFixture:
    if fixture_id == BUNDLED_FIXTURE_ID:
        return bundled_timeout_fixture()
    raise KeyError(f"unknown bundled fixture: {fixture_id}")
