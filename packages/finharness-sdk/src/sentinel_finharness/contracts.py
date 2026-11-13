"""Task-local typed snapshot of finharness-sdk.v1 and consumed wire shapes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

CONTRACT_VERSION = "sentinel.task-contracts.v1"
CONTRACT_SHA256 = "0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa"
PORT = "finharness-sdk.v1"

EvidenceMode = Literal["fixture", "real-peers"]
PeerName = Literal[
    "evidence.v1",
    "policy.v1",
    "action-ledger.v1",
    "verifier.v1",
    "indic-context.v1",
]


class ConfigurationError(ValueError):
    """Unsafe or incomplete SDK configuration; contains no secrets."""


class CapabilityDenied(PermissionError):
    """Routing, financial write, or notification capability is not explicitly enabled."""


class ContractViolation(ValueError):
    """Payload failed local contract shape checks."""


class PeerError(RuntimeError):
    """Injected peer unavailable, malformed, unauthorized, or out of scope."""

    def __init__(self, peer: PeerName, code: str, message: str) -> None:
        self.peer = peer
        self.code = code
        super().__init__(f"{peer}: {code}: {message}")


def require_mapping(value: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractViolation(f"{label} must be an object")
    return value


def require_str(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractViolation(f"{label} must be a non-empty string")
    return value


def require_int(value: Any, *, label: str, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractViolation(f"{label} must be an integer")
    if positive and value < 1:
        raise ContractViolation(f"{label} must be a positive integer")
    return value


def require_contract_version(value: Any) -> str:
    version = require_str(value, label="contract_version")
    if version != CONTRACT_VERSION:
        raise ContractViolation(f"contract_version must be {CONTRACT_VERSION}, got {version!r}")
    return version


def forbid_extra(payload: Mapping[str, Any], allowed: set[str], *, label: str) -> None:
    extra = set(payload) - allowed
    if extra:
        raise ContractViolation(f"{label} has undeclared fields: {sorted(extra)}")


def validate_evidence_collect(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_mapping(payload, label="EvidenceCollect")
    forbid_extra(payload, {"case_id", "case_revision", "order_reference"}, label="EvidenceCollect")
    return {
        "case_id": require_str(payload.get("case_id"), label="case_id"),
        "case_revision": require_int(
            payload.get("case_revision"), label="case_revision", positive=True
        ),
        "order_reference": require_str(payload.get("order_reference"), label="order_reference"),
    }


def validate_evidence_bundle(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_mapping(payload, label="EvidenceBundle")
    forbid_extra(
        payload,
        {"contract_version", "case_id", "evidence", "reconciliation_codes"},
        label="EvidenceBundle",
    )
    evidence = payload.get("evidence")
    codes = payload.get("reconciliation_codes")
    if not isinstance(evidence, list):
        raise ContractViolation("evidence must be an array")
    if not isinstance(codes, list):
        raise ContractViolation("reconciliation_codes must be an array")
    return {
        "contract_version": require_contract_version(payload.get("contract_version")),
        "case_id": require_str(payload.get("case_id"), label="case_id"),
        "evidence": evidence,
        "reconciliation_codes": codes,
    }


def validate_policy_request(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_mapping(payload, label="PolicyRequest")
    allowed = {"payload", "evidence", "approval"}
    forbid_extra(payload, allowed, label="PolicyRequest")
    action = require_mapping(payload.get("payload"), label="PolicyRequest.payload")
    evidence = payload.get("evidence")
    if not isinstance(evidence, list):
        raise ContractViolation("PolicyRequest.evidence must be an array")
    result: dict[str, Any] = {"payload": dict(action), "evidence": evidence}
    if "approval" in payload:
        result["approval"] = dict(require_mapping(payload["approval"], label="approval"))
    return result


def validate_policy_result(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_mapping(payload, label="PolicyResult")
    forbid_extra(
        payload,
        {"outcome", "reason_codes", "policy_version", "action_digest", "required_evidence"},
        label="PolicyResult",
    )
    outcome = require_str(payload.get("outcome"), label="outcome")
    if outcome not in {"ALLOW", "REQUIRE_APPROVAL", "DENY", "NEED_EVIDENCE"}:
        raise ContractViolation(f"unknown policy outcome {outcome!r}")
    reason_codes = payload.get("reason_codes")
    required_evidence = payload.get("required_evidence")
    if not isinstance(reason_codes, list) or not isinstance(required_evidence, list):
        raise ContractViolation("reason_codes and required_evidence must be arrays")
    return {
        "outcome": outcome,
        "reason_codes": reason_codes,
        "policy_version": require_str(payload.get("policy_version"), label="policy_version"),
        "action_digest": require_str(payload.get("action_digest"), label="action_digest"),
        "required_evidence": required_evidence,
    }


def validate_model_request(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_mapping(payload, label="ModelRequest")
    forbid_extra(payload, {"case", "input", "evidence"}, label="ModelRequest")
    case = require_mapping(payload.get("case"), label="ModelRequest.case")
    require_contract_version(case.get("contract_version"))
    evidence = payload.get("evidence")
    if not isinstance(evidence, list):
        raise ContractViolation("ModelRequest.evidence must be an array")
    return {
        "case": dict(case),
        "input": dict(require_mapping(payload.get("input"), label="ModelRequest.input")),
        "evidence": evidence,
    }


def validate_model_result(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_mapping(payload, label="ModelResult")
    forbid_extra(
        payload,
        {"outcome", "proposal", "reason_codes", "original_text", "language"},
        label="ModelResult",
    )
    outcome = require_str(payload.get("outcome"), label="outcome")
    if outcome not in {"PROPOSAL", "NEEDS_INPUT", "ESCALATE"}:
        raise ContractViolation(f"unknown model outcome {outcome!r}")
    reason_codes = payload.get("reason_codes")
    if not isinstance(reason_codes, list):
        raise ContractViolation("reason_codes must be an array")
    result = {
        "outcome": outcome,
        "reason_codes": reason_codes,
        "original_text": require_str(payload.get("original_text"), label="original_text"),
        "language": require_str(payload.get("language"), label="language"),
    }
    if outcome == "PROPOSAL":
        if "proposal" not in payload:
            raise ContractViolation("ModelResult.proposal required when outcome is PROPOSAL")
        result["proposal"] = dict(require_mapping(payload["proposal"], label="proposal"))
    elif "proposal" in payload:
        raise ContractViolation("ModelResult.proposal only allowed when outcome is PROPOSAL")
    return result


def validate_proposal_request(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_mapping(payload, label="ProposalRequest")
    forbid_extra(payload, {"operation_key", "payload", "action_digest"}, label="ProposalRequest")
    return {
        "operation_key": require_str(payload.get("operation_key"), label="operation_key"),
        "payload": dict(require_mapping(payload.get("payload"), label="ProposalRequest.payload")),
        "action_digest": require_str(payload.get("action_digest"), label="action_digest"),
    }


def validate_reservation_request(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_mapping(payload, label="ReservationRequest")
    forbid_extra(
        payload,
        {"operation_key", "payload", "action_digest", "approval_id"},
        label="ReservationRequest",
    )
    return {
        "operation_key": require_str(payload.get("operation_key"), label="operation_key"),
        "payload": dict(
            require_mapping(payload.get("payload"), label="ReservationRequest.payload")
        ),
        "action_digest": require_str(payload.get("action_digest"), label="action_digest"),
        "approval_id": require_str(payload.get("approval_id"), label="approval_id"),
    }


def validate_action_record(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_mapping(payload, label="ActionRecord")
    forbid_extra(
        payload,
        {"action_id", "provider_ref", "payload", "action_digest", "status", "approval"},
        label="ActionRecord",
    )
    result = {
        "action_id": require_str(payload.get("action_id"), label="action_id"),
        "provider_ref": require_str(payload.get("provider_ref"), label="provider_ref"),
        "payload": dict(require_mapping(payload.get("payload"), label="ActionRecord.payload")),
        "action_digest": require_str(payload.get("action_digest"), label="action_digest"),
        "status": require_str(payload.get("status"), label="status"),
    }
    if "approval" in payload:
        result["approval"] = dict(require_mapping(payload["approval"], label="approval"))
    return result


def validate_verification_request(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_mapping(payload, label="VerificationRequest")
    forbid_extra(
        payload,
        {"case_id", "case_revision", "action_id", "provider_ref"},
        label="VerificationRequest",
    )
    return {
        "case_id": require_str(payload.get("case_id"), label="case_id"),
        "case_revision": require_int(
            payload.get("case_revision"), label="case_revision", positive=True
        ),
        "action_id": require_str(payload.get("action_id"), label="action_id"),
        "provider_ref": require_str(payload.get("provider_ref"), label="provider_ref"),
    }


def validate_verification_result(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_mapping(payload, label="VerificationResult")
    forbid_extra(
        payload,
        {
            "assessment_id",
            "case_id",
            "case_revision",
            "action_id",
            "assessed_at",
            "expires_at",
            "status",
            "evidence",
            "reason_codes",
        },
        label="VerificationResult",
    )
    status = require_str(payload.get("status"), label="status")
    if status not in {"WAITING", "VERIFIED", "CONFLICT", "ESCALATED"}:
        raise ContractViolation(f"unknown verification status {status!r}")
    evidence = payload.get("evidence")
    reason_codes = payload.get("reason_codes")
    if not isinstance(evidence, list) or not isinstance(reason_codes, list):
        raise ContractViolation("evidence and reason_codes must be arrays")
    return {
        "assessment_id": require_str(payload.get("assessment_id"), label="assessment_id"),
        "case_id": require_str(payload.get("case_id"), label="case_id"),
        "case_revision": require_int(
            payload.get("case_revision"), label="case_revision", positive=True
        ),
        "action_id": require_str(payload.get("action_id"), label="action_id"),
        "assessed_at": require_str(payload.get("assessed_at"), label="assessed_at"),
        "expires_at": require_str(payload.get("expires_at"), label="expires_at"),
        "status": status,
        "evidence": evidence,
        "reason_codes": reason_codes,
    }
