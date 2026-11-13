from __future__ import annotations

import pytest
from conftest import make_runtime

from sentinel_finharness_runtime.domain.errors import CapabilityDenied, SafetyViolation


def test_shadow_has_no_write_adapter_credentials_or_notifications(
    shadow_config, manifest, baseline
):
    runtime = make_runtime(shadow_config)
    pin = runtime.start_case(case_id="case-demo-42", tenant_id="sandbox", manifest=manifest)
    comparison = runtime.run_shadow(case_id=pin.case_id, baseline_proposal=baseline)

    assert comparison.write_adapter_present is False
    assert comparison.credentials_present is False
    assert comparison.notifications_attempted >= 1  # probed and blocked
    assert "NO_SECOND_REFUND" in comparison.reason_codes
    assert "NO_WRITE_ADAPTER" in comparison.reason_codes
    assert "NOTIFICATIONS_BLOCKED" in comparison.reason_codes
    assert comparison.proposals_match is True


def test_shadow_cannot_send_second_refund(shadow_config, manifest, baseline):
    runtime = make_runtime(shadow_config)
    runtime.start_case(case_id="case-demo-42", tenant_id="sandbox", manifest=manifest)
    comparison = runtime.run_shadow(case_id="case-demo-42", baseline_proposal=baseline)

    with pytest.raises(CapabilityDenied, match="create_proposal"):
        runtime.ports.ledger.create_proposal(
            {"operation_key": "x", "payload": {}, "action_digest": "y"}
        )
    with pytest.raises(CapabilityDenied, match="reserve"):
        runtime.ports.ledger.reserve(
            {
                "operation_key": "x",
                "payload": {},
                "action_digest": "y",
                "approval_id": "a",
            }
        )
    with pytest.raises(SafetyViolation, match="second refund"):
        runtime.ports.safety.attempt_refund_write(provider_ref="refund-demo-2")

    assert comparison.refund_write_attempts >= 1
    assert comparison.write_adapter_present is False


def test_shadow_route_never_enables_financial_writes(shadow_config, manifest):
    runtime = make_runtime(shadow_config)
    runtime.start_case(case_id="case-demo-42", tenant_id="sandbox", manifest=manifest)
    decision = runtime.route_sandbox("case-demo-42")
    assert decision.routed is True
    assert decision.financial_writes is False
    assert decision.reason_code == "SHADOW_READ_ONLY"
