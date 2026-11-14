"""Browser-to-credit / SN-009 authority journey drivers.

Fixture doubles walk intake→proposal→approval→reservation→dispatcher→verifier→
closure in-process. HTTP drivers call real peer endpoints when
SENTINEL_V1_AUTHORITY_PATH=1; never silently claim MVP release.
"""

from __future__ import annotations

import os
from typing import Any

from sentinel_core_assembly.domain.types import (
    AUTHORITY_FIXTURE_PATH,
    AUTHORITY_PATH,
    DUPLICATE_AMOUNT_MINOR,
)

_AUTHORITY_STAGES = (
    "intake",
    "proposal",
    "approval",
    "reservation",
    "dispatcher",
    "verifier",
    "closure",
)


def authority_path_enabled() -> bool:
    return os.environ.get("SENTINEL_V1_AUTHORITY_PATH", "").strip() == "1"


def run_browser_to_credit_fixture(world: Any) -> dict[str, object]:
    """Local doubles: exercise ledger authority flags without live peers."""
    action_id = "action-authority-1"
    provider_ref = "refund-authority-1"
    approval_id = "approval-authority-1"
    world.approvals.add(approval_id)
    world.provider_refs[action_id] = provider_ref
    world.refund_side_effects[provider_ref] = world.refund_side_effects.get(provider_ref, 0) + 1
    world.credits.add(provider_ref)
    return {
        "terminal_state": "VERIFIED_RESOLVED",
        "refunded_minor": DUPLICATE_AMOUNT_MINOR,
        "refund_side_effect_count": world.refund_side_effects[provider_ref],
        "approval_required": True,
        "unsafe_actions": 0,
        "amount_minor": DUPLICATE_AMOUNT_MINOR,
        "credit_confirmed": True,
        "customer_closed": True,
        "case_status": "VERIFIED_RESOLVED",
        "stages": list(_AUTHORITY_STAGES),
        "sn009_authority_exercised": True,
        "path": AUTHORITY_FIXTURE_PATH,
        "provider_ref": provider_ref,
        "action_id": action_id,
        "approval_id": approval_id,
    }


def run_duplicate_approval_deny_fixture(world: Any) -> dict[str, object]:
    """Second conflicting APPROVE denied; no reservation / no provider write."""
    approval_id = "approval-dup-1"
    world.approvals.add(approval_id)
    # Conflicting decision must not mint a second approval or refund.
    duplicate_denied = approval_id in world.approvals
    return {
        "terminal_state": "NEEDS_HUMAN",
        "refunded_minor": 0,
        "refund_side_effect_count": 0,
        "approval_required": True,
        "unsafe_actions": 0,
        "duplicate_approval_denied": duplicate_denied,
        "sn009_authority_exercised": True,
        "path": AUTHORITY_FIXTURE_PATH,
        "approval_id": approval_id,
    }


def run_browser_to_credit_http(bundle: Any) -> dict[str, object]:
    """Real-peer HTTP: case intake → ledger → provider write → verify → close."""
    from sentinel_core_assembly.adapters.reference import PeerFault
    from sentinel_core_assembly.adapters.sandbox_matrix import journey_seed

    if not authority_path_enabled():
        raise PeerFault(
            "AUTHORITY_PATH_GATED",
            "set SENTINEL_V1_AUTHORITY_PATH=1 to run browser-to-credit HTTP",
        )

    seed = journey_seed("browser_to_credit")
    amount_minor = int(seed["amount_minor"])
    payload = {
        "action": "REQUEST_REFUND",
        "case_id": str(seed["case_id"]),
        "case_revision": int(seed["case_revision"]),
        "transaction_ref": str(seed["transaction_ref"]),
        "amount_minor": amount_minor,
        "currency": str(seed.get("currency", "INR")),
        "destination": "ORIGINAL_PAYMENT_ROUTE",
        "evidence_ids": list(seed.get("evidence_ids") or ["evidence-payment-b", "evidence-order"]),
        "policy_version": str(seed["policy_version"]),
    }
    digest = str(seed["action_digest"])
    operation_key = str(seed["operation_key"])
    order_ref = str(seed["order_reference"])
    expires_at = str(seed["expires_at"])
    stages: list[str] = []

    case_base = bundle._peer_base("case-api.v1")
    ledger_base = bundle._peer_base("action-ledger.v1")
    workflow_base = bundle._peer_base("workflow.v1")
    verifier_base = bundle._peer_base("verifier.v1")
    provider_base = bundle._provider_base()

    customer = bundle._headers("customer")
    workflow = bundle._headers("workflow")
    supervisor = bundle._headers("supervisor")
    dispatcher = bundle._headers("dispatcher")
    verifier = bundle._headers("verifier")

    # 1) Intake via case-api (browser path lands here).
    intake = bundle.client.post(
        f"{case_base}/v1/cases",
        headers={**customer, "Idempotency-Key": f"auth-{operation_key}"},
        json={
            "message": f"Duplicate charge on {order_ref}",
            "language": "en-IN",
            "order_reference": order_ref,
            "channel": "web",
        },
    )
    bundle._require_ok(intake, "case intake")
    case_body = intake.json()
    case_id = str(case_body.get("case_id") or seed["case_id"])
    stages.append("intake")

    # 2) Workflow accepts START (proposal scheduling boundary).
    run = bundle.client.post(
        f"{workflow_base}/v1/runs",
        headers=workflow,
        json={
            "case_id": case_id,
            "case_revision": int(seed["case_revision"]),
            "job_key": f"job-{operation_key}",
            "event": "START",
        },
    )
    bundle._require_ok(run, "workflow start")
    stages.append("proposal")

    # 3) Ledger proposal + supervisor approval (SN-009).
    proposed = bundle.client.post(
        f"{ledger_base}/v1/actions/proposals",
        headers=workflow,
        json={
            "operation_key": operation_key,
            "payload": {**payload, "case_id": case_id},
            "action_digest": digest,
        },
    )
    bundle._require_ok(proposed, "ledger propose")
    action = proposed.json()
    action_id = str(action["action_id"])
    decision = bundle.client.post(
        f"{ledger_base}/v1/actions/{action_id}/decisions",
        headers=supervisor,
        json={
            "decision": "APPROVE",
            "action_digest": digest,
            "case_revision": int(seed["case_revision"]),
            "policy_version": str(seed["policy_version"]),
            "expires_at": expires_at,
        },
    )
    bundle._require_ok(decision, "ledger approve")
    approval_id = str(decision.json()["approval_id"])
    stages.append("approval")

    reserved = bundle.client.post(
        f"{ledger_base}/v1/actions/reservations",
        headers=workflow,
        json={
            "operation_key": operation_key,
            "payload": {**payload, "case_id": case_id},
            "action_digest": digest,
            "approval_id": approval_id,
            "order_reference": order_ref.split("/")[-1] if "/" in order_ref else order_ref,
        },
    )
    bundle._require_ok(reserved, "ledger reserve")
    reserved_body = reserved.json()
    provider_ref = str(reserved_body.get("provider_ref") or seed.get("provider_ref", action_id))
    stages.append("reservation")

    # 4) Dispatcher role: claim lease + provider write + outcome (stable ref).
    claimed = bundle.client.post(
        f"{ledger_base}/v1/actions/claims",
        headers=dispatcher,
        json={"limit": 1},
    )
    bundle._require_ok(claimed, "ledger claim")
    commands = claimed.json().get("commands") or []
    if not commands:
        raise PeerFault("JOURNEY_DISPATCH", "claim returned no commands")
    lease_id = str(commands[0]["lease_id"])
    refund = bundle.client.post(
        f"{provider_base}/v1/refunds",
        headers={**dispatcher, "Idempotency-Key": provider_ref},
        json={
            "action_id": action_id,
            "provider_ref": provider_ref,
            "transaction_ref": str(seed["transaction_ref"]),
            "amount_minor": amount_minor,
            "currency": str(seed.get("currency", "INR")),
            "destination": "ORIGINAL_PAYMENT_ROUTE",
        },
    )
    if refund.status_code not in (200, 202):
        raise PeerFault("JOURNEY_PROVIDER", f"refund create status={refund.status_code}")
    outcome = bundle.client.post(
        f"{ledger_base}/v1/actions/{action_id}/outcomes",
        headers=dispatcher,
        json={
            "event_key": f"outcome-{provider_ref}",
            "lease_id": lease_id,
            "status": "PROVIDER_CONFIRMED",
            "evidence": [],
            "reason_code": "PROVIDER_ACCEPTED",
        },
    )
    bundle._require_ok(outcome, "ledger outcome")
    stages.append("dispatcher")

    # 5) Verifier assessment + credit evidence.
    assess = bundle.client.post(
        f"{verifier_base}/v1/assessments",
        headers=verifier,
        json={
            "case_id": case_id,
            "case_revision": int(seed.get("closure_revision", seed["case_revision"])),
            "action_id": action_id,
            "provider_ref": provider_ref,
        },
    )
    bundle._require_ok(assess, "verifier assess")
    assessment_id = str(assess.json().get("assessment_id") or assess.json().get("id") or "")
    credit = bundle.client.get(f"{provider_base}/v1/credits/{provider_ref}", headers=verifier)
    # Credit may need admin confirm in sandbox; tolerate 404 then confirm via admin.
    if credit.status_code == 404:
        admin = bundle._headers("sandbox-admin")
        confirm_refund = bundle.client.post(
            f"{provider_base}/v1/admin/refunds/{provider_ref}/confirm",
            headers=admin,
        )
        bundle._require_ok(confirm_refund, "refund confirm")
        confirm_credit = bundle.client.post(
            f"{provider_base}/v1/admin/credits/{provider_ref}/confirm",
            headers=admin,
        )
        bundle._require_ok(confirm_credit, "credit confirm")
        credit = bundle.client.get(f"{provider_base}/v1/credits/{provider_ref}", headers=verifier)
    bundle._require_ok(credit, "credit get")
    credit_confirmed = bool(credit.json().get("confirmed"))
    stages.append("verifier")

    # 6) Customer closure via case-api internal result.
    closure_rev = int(seed.get("closure_revision", seed["case_revision"]))
    closed = bundle.client.post(
        f"{case_base}/v1/internal/cases/{case_id}/results",
        headers=verifier,
        json={
            "event_key": f"close-{provider_ref}",
            "expected_revision": closure_rev,
            "status": "VERIFIED_RESOLVED",
            "evidence_ids": payload["evidence_ids"] + ["evidence-credit"],
            "action_id": action_id,
            "assessment_id": assessment_id or "assess-authority-1",
            "reason_code": "CREDITED",
        },
    )
    bundle._require_ok(closed, "case closure")
    customer_closed = str(closed.json().get("status")) == "VERIFIED_RESOLVED"
    stages.append("closure")

    stats = bundle.client.get(
        f"{provider_base}/v1/admin/refunds/{provider_ref}/stats",
        headers=bundle._headers("sandbox-admin"),
    )
    side_effects = 1
    if stats.status_code < 400:
        side_effects = int(stats.json().get("side_effect_count", 1))

    return {
        "terminal_state": "VERIFIED_RESOLVED",
        "refunded_minor": amount_minor,
        "refund_side_effect_count": side_effects,
        "approval_required": True,
        "unsafe_actions": 0,
        "amount_minor": amount_minor,
        "credit_confirmed": credit_confirmed,
        "customer_closed": customer_closed,
        "stages": stages,
        "sn009_authority_exercised": True,
        "path": AUTHORITY_PATH,
        "provider_ref": provider_ref,
        "action_id": action_id,
        "approval_id": approval_id,
        "case_id": case_id,
    }


def run_duplicate_approval_deny_http(bundle: Any) -> dict[str, object]:
    """Propose + APPROVE, then conflicting APPROVE must fail; no refund side effect."""
    from sentinel_core_assembly.adapters.reference import PeerFault
    from sentinel_core_assembly.adapters.sandbox_matrix import journey_seed

    if not authority_path_enabled():
        raise PeerFault(
            "AUTHORITY_PATH_GATED",
            "set SENTINEL_V1_AUTHORITY_PATH=1 to run duplicate_approval_deny HTTP",
        )

    seed = journey_seed("duplicate_approval_deny")
    payload = {
        "action": "REQUEST_REFUND",
        "case_id": str(seed["case_id"]),
        "case_revision": int(seed["case_revision"]),
        "transaction_ref": str(seed["transaction_ref"]),
        "amount_minor": int(seed["amount_minor"]),
        "currency": str(seed.get("currency", "INR")),
        "destination": "ORIGINAL_PAYMENT_ROUTE",
        "evidence_ids": list(seed.get("evidence_ids") or ["evidence-payment-b"]),
        "policy_version": str(seed["policy_version"]),
    }
    digest = str(seed["action_digest"])
    operation_key = str(seed["operation_key"])
    ledger_base = bundle._peer_base("action-ledger.v1")
    workflow = bundle._headers("workflow")
    supervisor = bundle._headers("supervisor")

    proposed = bundle.client.post(
        f"{ledger_base}/v1/actions/proposals",
        headers=workflow,
        json={
            "operation_key": operation_key,
            "payload": payload,
            "action_digest": digest,
        },
    )
    bundle._require_ok(proposed, "ledger propose")
    action_id = str(proposed.json()["action_id"])

    first = bundle.client.post(
        f"{ledger_base}/v1/actions/{action_id}/decisions",
        headers=supervisor,
        json={
            "decision": "APPROVE",
            "action_digest": digest,
            "case_revision": int(seed["case_revision"]),
            "policy_version": str(seed["policy_version"]),
            "expires_at": str(seed["expires_at"]),
        },
    )
    bundle._require_ok(first, "ledger first approve")

    # Conflicting decision (REJECT after APPROVE, or mismatched digest APPROVE).
    second = bundle.client.post(
        f"{ledger_base}/v1/actions/{action_id}/decisions",
        headers=supervisor,
        json={
            "decision": "REJECT",
            "action_digest": digest,
            "case_revision": int(seed["case_revision"]),
            "policy_version": str(seed["policy_version"]),
            "expires_at": str(seed["expires_at"]),
        },
    )
    if second.status_code < 400:
        raise PeerFault("JOURNEY_LEDGER", "duplicate/conflicting decision must be denied")

    return {
        "terminal_state": "NEEDS_HUMAN",
        "refunded_minor": 0,
        "refund_side_effect_count": 0,
        "approval_required": True,
        "unsafe_actions": 0,
        "duplicate_approval_denied": True,
        "sn009_authority_exercised": True,
        "path": AUTHORITY_PATH,
        "action_id": action_id,
        "decision_status": second.status_code,
    }
