import pytest
from stubs import (
    MalformedActionLedger,
    MalformedEvidence,
    UnauthorizedActionLedger,
    UnavailableEvidence,
    ValidActionLedger,
    ValidEvidence,
    ValidIndicContext,
    ValidPolicy,
    ValidVerifier,
)
from stubs._payloads import DIGEST, REFUND_ACTION

from sentinel_finharness import (
    CapabilityDenied,
    ContractViolation,
    FinHarnessClient,
    PeerError,
    RuntimeConfig,
)


def _client(manifest, config, **peers):
    defaults = {
        "evidence": ValidEvidence(),
        "policy": ValidPolicy(),
        "ledger": ValidActionLedger(),
        "verifier": ValidVerifier(),
        "indic_context": ValidIndicContext(),
    }
    defaults.update(peers)
    return FinHarnessClient(
        config=config,
        manifest=manifest,
        tenant_id="sandbox",
        **defaults,
    )


def test_disabled_routing_blocks_peer_calls(manifest):
    client = _client(manifest, RuntimeConfig())
    with pytest.raises(CapabilityDenied, match="routing disabled"):
        client.collect_evidence(
            {
                "case_id": "case-demo-42",
                "case_revision": 1,
                "order_reference": "DEMO-ORDER-42",
            }
        )


def test_shadow_forbids_financial_writes(manifest, enabled_shadow):
    client = _client(manifest, enabled_shadow)
    with pytest.raises(CapabilityDenied, match="shadow"):
        client.create_proposal(
            {
                "operation_key": "k",
                "payload": REFUND_ACTION,
                "action_digest": DIGEST,
            }
        )


def test_harness_without_writes_blocks_reserve(manifest):
    config = RuntimeConfig.from_mapping(
        {
            "enabled": True,
            "execution_mode": "harness",
            "financial_writes": False,
            "allowed_workflows": [manifest.workflow_name],
            "allowed_tenants": ["sandbox"],
        }
    )
    client = _client(manifest, config)
    with pytest.raises(CapabilityDenied, match="financial_writes"):
        client.reserve(
            {
                "operation_key": "k",
                "payload": REFUND_ACTION,
                "action_digest": DIGEST,
                "approval_id": "synthetic-approval_id",
            }
        )


def test_notifications_disabled_by_default(manifest, enabled_harness):
    client = _client(manifest, enabled_harness)
    with pytest.raises(CapabilityDenied, match="notifications"):
        client.notify(channel="operator", message_code="WAITING")


def test_bypass_helper_never_calls_ledger(manifest, enabled_harness):
    client = _client(manifest, enabled_harness)
    with pytest.raises(CapabilityDenied, match="approval_id"):
        client.bypass_reserve_without_approval(
            {
                "operation_key": "k",
                "payload": REFUND_ACTION,
                "action_digest": DIGEST,
            }
        )


def test_reserve_requires_approval_id_in_payload(manifest, enabled_harness):
    client = _client(manifest, enabled_harness)
    with pytest.raises(ContractViolation, match="approval_id"):
        client.reserve(
            {
                "operation_key": "k",
                "payload": REFUND_ACTION,
                "action_digest": DIGEST,
            }
        )


def test_peer_unavailable_surfaces(manifest, enabled_shadow):
    client = _client(manifest, enabled_shadow, evidence=UnavailableEvidence())
    with pytest.raises(PeerError) as exc:
        client.collect_evidence(
            {
                "case_id": "case-demo-42",
                "case_revision": 1,
                "order_reference": "DEMO-ORDER-42",
            }
        )
    assert exc.value.peer == "evidence.v1"
    assert exc.value.code == "unavailable"


def test_peer_malformed_surfaces(manifest, enabled_shadow):
    client = _client(manifest, enabled_shadow, evidence=MalformedEvidence())
    with pytest.raises(ContractViolation):
        client.collect_evidence(
            {
                "case_id": "case-demo-42",
                "case_revision": 1,
                "order_reference": "DEMO-ORDER-42",
            }
        )


def test_peer_unauthorized_surfaces(manifest, enabled_harness):
    client = _client(manifest, enabled_harness, ledger=UnauthorizedActionLedger())
    with pytest.raises(PeerError) as exc:
        client.create_proposal(
            {
                "operation_key": "k",
                "payload": REFUND_ACTION,
                "action_digest": DIGEST,
            }
        )
    assert exc.value.code == "unauthorized_or_out_of_scope"


def test_malformed_ledger_response_rejected(manifest, enabled_harness):
    client = _client(manifest, enabled_harness, ledger=MalformedActionLedger())
    with pytest.raises(ContractViolation):
        client.create_proposal(
            {
                "operation_key": "k",
                "payload": REFUND_ACTION,
                "action_digest": DIGEST,
            }
        )


def test_tenant_allowlist(manifest, enabled_shadow):
    with pytest.raises(CapabilityDenied, match="tenant"):
        FinHarnessClient(
            config=enabled_shadow,
            manifest=manifest,
            evidence=ValidEvidence(),
            policy=ValidPolicy(),
            ledger=ValidActionLedger(),
            verifier=ValidVerifier(),
            indic_context=ValidIndicContext(),
            tenant_id="other-tenant",
        )
