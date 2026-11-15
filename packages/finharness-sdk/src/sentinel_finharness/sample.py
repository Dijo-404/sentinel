"""Local sample workflow against injected ports. Fixture mode only."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from .client import FinHarnessClient
from .config import RuntimeConfig
from .contracts import CONTRACT_SHA256, CONTRACT_VERSION, PORT, CapabilityDenied
from .manifest import CaseManifest
from .ports import (
    ActionLedgerPort,
    EvidencePort,
    IndicContextPort,
    NotificationPort,
    PolicyPort,
    VerifierPort,
)


class MemoryNotificationQueue:
    """In-process queue for fixture samples — records enqueues instead of inventing success."""

    def __init__(self) -> None:
        self.items: list[dict[str, str]] = []

    def enqueue(self, *, channel: str, message_code: str) -> dict[str, str]:
        item = {"status": "queued", "channel": channel, "message_code": message_code}
        self.items.append(item)
        return dict(item)


@dataclass(frozen=True)
class SampleReport:
    contract_version: Literal["sentinel.task-contracts.v1"]
    port: Literal["finharness-sdk.v1"]
    baseline_sha256: str
    evidence_mode: Literal["fixture"]
    workflow: str
    workflow_version: str
    routing_enabled: bool
    financial_writes: bool
    notifications: bool
    steps: tuple[str, ...]
    policy_outcome: str | None
    model_outcome: str | None
    action_id: str | None
    assessment_status: str | None


def _default_collect(case_id: str, case_revision: int, order_reference: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "case_revision": case_revision,
        "order_reference": order_reference,
    }


def _default_model_request(
    *,
    case_id: str,
    case_revision: int,
    order_reference: str,
    evidence: list[Any],
) -> dict[str, Any]:
    return {
        "case": {
            "contract_version": CONTRACT_VERSION,
            "case_id": case_id,
            "revision": case_revision,
            "status": "RECEIVED",
            "language": "en-IN",
            "intent": "duplicate_payment",
            "evidence_ids": [e.get("evidence_id") for e in evidence if isinstance(e, Mapping)],
        },
        "input": {
            "case_id": case_id,
            "case_revision": case_revision,
            "original_text": "Synthetic duplicate payment complaint",
            "language": "en-IN",
            "order_reference": order_reference,
            "messages": [],
        },
        "evidence": evidence,
    }


def run_sample_workflow(
    *,
    config: RuntimeConfig,
    manifest: CaseManifest,
    evidence: EvidencePort,
    policy: PolicyPort,
    ledger: ActionLedgerPort,
    verifier: VerifierPort,
    indic_context: IndicContextPort,
    tenant_id: str = "sandbox",
    case_id: str = "case-demo-42",
    case_revision: int = 1,
    order_reference: str = "DEMO-ORDER-42",
    approval_id: str | None = None,
    notifications: NotificationPort | None = None,
) -> SampleReport:
    """
    Exercise read/shadow or explicit harness write path via the SDK.

    Default config refuses routing. Callers must pass an explicitly enabled config
    for any peer traffic. Financial writes still require financial_writes=True,
    harness mode, and a real approval_id for reservation.
    """
    notify_port = notifications
    if config.notifications and notify_port is None:
        notify_port = MemoryNotificationQueue()
    client = FinHarnessClient(
        config=config,
        manifest=manifest,
        evidence=evidence,
        policy=policy,
        ledger=ledger,
        verifier=verifier,
        indic_context=indic_context,
        tenant_id=tenant_id,
        notifications=notify_port,
    )
    steps: list[str] = []
    policy_outcome: str | None = None
    model_outcome: str | None = None
    action_id: str | None = None
    assessment_status: str | None = None

    if not config.routing_active():
        steps.append("routing-disabled")
        return SampleReport(
            contract_version=CONTRACT_VERSION,
            port=PORT,
            baseline_sha256=CONTRACT_SHA256,
            evidence_mode="fixture",
            workflow=manifest.workflow_name,
            workflow_version=manifest.workflow_version,
            routing_enabled=False,
            financial_writes=False,
            notifications=False,
            steps=tuple(steps),
            policy_outcome=None,
            model_outcome=None,
            action_id=None,
            assessment_status=None,
        )

    bundle = client.collect_evidence(_default_collect(case_id, case_revision, order_reference))
    steps.append("evidence-collected")
    model = client.propose(
        _default_model_request(
            case_id=case_id,
            case_revision=case_revision,
            order_reference=order_reference,
            evidence=list(bundle["evidence"]),
        )
    )
    model_outcome = str(model["outcome"])
    steps.append("model-proposed")

    if model_outcome != "PROPOSAL" or "proposal" not in model:
        steps.append("no-refund-proposal")
        return SampleReport(
            contract_version=CONTRACT_VERSION,
            port=PORT,
            baseline_sha256=CONTRACT_SHA256,
            evidence_mode="fixture",
            workflow=manifest.workflow_name,
            workflow_version=manifest.workflow_version,
            routing_enabled=True,
            financial_writes=config.financial_writes,
            notifications=config.notifications,
            steps=tuple(steps),
            policy_outcome=None,
            model_outcome=model_outcome,
            action_id=None,
            assessment_status=None,
        )

    proposal = model["proposal"]
    policy_result = client.evaluate_policy({"payload": proposal, "evidence": bundle["evidence"]})
    policy_outcome = str(policy_result["outcome"])
    steps.append("policy-evaluated")

    if config.execution_mode == "shadow" or not config.financial_writes:
        steps.append("shadow-or-writes-disabled")
        return SampleReport(
            contract_version=CONTRACT_VERSION,
            port=PORT,
            baseline_sha256=CONTRACT_SHA256,
            evidence_mode="fixture",
            workflow=manifest.workflow_name,
            workflow_version=manifest.workflow_version,
            routing_enabled=True,
            financial_writes=config.financial_writes,
            notifications=config.notifications,
            steps=tuple(steps),
            policy_outcome=policy_outcome,
            model_outcome=model_outcome,
            action_id=None,
            assessment_status=None,
        )

    if policy_outcome not in {"ALLOW", "REQUIRE_APPROVAL"}:
        steps.append("policy-denied")
        return SampleReport(
            contract_version=CONTRACT_VERSION,
            port=PORT,
            baseline_sha256=CONTRACT_SHA256,
            evidence_mode="fixture",
            workflow=manifest.workflow_name,
            workflow_version=manifest.workflow_version,
            routing_enabled=True,
            financial_writes=True,
            notifications=config.notifications,
            steps=tuple(steps),
            policy_outcome=policy_outcome,
            model_outcome=model_outcome,
            action_id=None,
            assessment_status=None,
        )

    digest = str(policy_result["action_digest"])
    record = client.create_proposal(
        {
            "operation_key": f"{case_id}:{case_revision}:refund",
            "payload": proposal,
            "action_digest": digest,
        }
    )
    action_id = str(record["action_id"])
    steps.append("ledger-proposal")

    if not approval_id:
        steps.append("awaiting-approval")
        return SampleReport(
            contract_version=CONTRACT_VERSION,
            port=PORT,
            baseline_sha256=CONTRACT_SHA256,
            evidence_mode="fixture",
            workflow=manifest.workflow_name,
            workflow_version=manifest.workflow_version,
            routing_enabled=True,
            financial_writes=True,
            notifications=config.notifications,
            steps=tuple(steps),
            policy_outcome=policy_outcome,
            model_outcome=model_outcome,
            action_id=action_id,
            assessment_status=None,
        )

    reserved = client.reserve(
        {
            "operation_key": f"{case_id}:{case_revision}:refund",
            "payload": proposal,
            "action_digest": digest,
            "approval_id": approval_id,
        }
    )
    action_id = str(reserved["action_id"])
    steps.append("ledger-reserved")

    assessment = client.assess(
        {
            "case_id": case_id,
            "case_revision": case_revision,
            "action_id": action_id,
            "provider_ref": reserved["provider_ref"],
        }
    )
    assessment_status = str(assessment["status"])
    steps.append("verifier-assessed")

    if config.notifications:
        client.notify(channel="operator", message_code="WAITING")
        steps.append("notification-queued")
    else:
        try:
            client.notify(channel="operator", message_code="WAITING")
        except CapabilityDenied:
            steps.append("notification-blocked")

    return SampleReport(
        contract_version=CONTRACT_VERSION,
        port=PORT,
        baseline_sha256=CONTRACT_SHA256,
        evidence_mode="fixture",
        workflow=manifest.workflow_name,
        workflow_version=manifest.workflow_version,
        routing_enabled=True,
        financial_writes=True,
        notifications=config.notifications,
        steps=tuple(steps),
        policy_outcome=policy_outcome,
        model_outcome=model_outcome,
        action_id=action_id,
        assessment_status=assessment_status,
    )
