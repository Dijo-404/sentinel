"""Task-local typed snapshot of policy.v1 wire types and digest rules."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Literal

CONTRACT_VERSION = "sentinel.task-contracts.v1"
CONTRACT_SHA256 = "0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa"
PORT = "policy.v1"
POLICY_VERSION = "demo-policy-v1"
COMPONENT = "policy"

Outcome = Literal["ALLOW", "REQUIRE_APPROVAL", "DENY", "NEED_EVIDENCE"]
VerificationStatus = Literal["VERIFIED", "UNVERIFIED", "CONFLICTING"]
PaymentStatus = Literal["CAPTURED", "PENDING", "FAILED"]
Decision = Literal["APPROVE", "REJECT"]
Destination = Literal["ORIGINAL_PAYMENT_ROUTE"]

REFUND_ACTION_KEYS = frozenset(
    {
        "action",
        "case_id",
        "case_revision",
        "transaction_ref",
        "amount_minor",
        "currency",
        "destination",
        "evidence_ids",
        "policy_version",
    }
)


class PolicyInputError(ValueError):
    """Malformed policy request; safe for API 422 mapping."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Principal:
    principal_id: str
    tenant_id: str
    roles: tuple[str, ...]
    subject_refs: tuple[str, ...]
    case_ids: tuple[str, ...]


@dataclass(frozen=True)
class Payment:
    transaction_ref: str
    order_reference: str
    subject_ref: str
    status: PaymentStatus
    amount_minor: int
    currency: Literal["INR"]


@dataclass(frozen=True)
class Order:
    order_reference: str
    subject_ref: str
    fulfilled_order_count: int
    merchant_confirmed_duplicate: bool
    paid: bool


@dataclass(frozen=True)
class Refund:
    action_id: str
    provider_ref: str
    transaction_ref: str
    amount_minor: int
    currency: Literal["INR"]
    status: Literal["PENDING", "PROVIDER_CONFIRMED", "FAILED_FINAL"]


@dataclass(frozen=True)
class Credit:
    provider_ref: str
    confirmed: bool
    observed_at: str


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    case_id: str
    source: str
    subject_ref: str
    observed_at: str
    expires_at: str
    digest: str
    verification_status: VerificationStatus
    facts: dict[str, Any]


@dataclass(frozen=True)
class Approval:
    approval_id: str
    action_digest: str
    case_revision: int
    policy_version: str
    decision: Decision
    reviewer_id: str
    expires_at: str


@dataclass(frozen=True)
class RefundAction:
    action: Literal["REQUEST_REFUND"]
    case_id: str
    case_revision: int
    transaction_ref: str
    amount_minor: int
    currency: Literal["INR"]
    destination: str
    evidence_ids: tuple[str, ...]
    policy_version: str

    def as_digest_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "amount_minor": self.amount_minor,
            "case_id": self.case_id,
            "case_revision": self.case_revision,
            "currency": self.currency,
            "destination": self.destination,
            "evidence_ids": list(self.evidence_ids),
            "policy_version": self.policy_version,
            "transaction_ref": self.transaction_ref,
        }


@dataclass(frozen=True)
class GenericAction:
    action: str
    case_id: str
    case_revision: int
    evidence_ids: tuple[str, ...]
    policy_version: str
    fields: dict[str, Any] = field(default_factory=dict)

    def as_digest_dict(self) -> dict[str, Any]:
        payload = {
            "action": self.action,
            "case_id": self.case_id,
            "case_revision": self.case_revision,
            "evidence_ids": list(self.evidence_ids),
            "policy_version": self.policy_version,
            **self.fields,
        }
        return payload


Action = RefundAction | GenericAction


@dataclass(frozen=True)
class PolicyRequest:
    payload: Action
    evidence: tuple[Evidence, ...]
    approval: Approval | None = None


@dataclass(frozen=True)
class PolicyResult:
    outcome: Outcome
    reason_codes: tuple[str, ...]
    policy_version: str
    action_digest: str
    required_evidence: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "reason_codes": list(self.reason_codes),
            "policy_version": self.policy_version,
            "action_digest": self.action_digest,
            "required_evidence": list(self.required_evidence),
        }


def canonical_action_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def action_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_action_bytes(payload)).hexdigest()


def _require_str(obj: dict[str, Any], key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value:
        raise PolicyInputError("INVALID_INPUT", f"Field '{key}' must be a nonempty string")
    return value


def _require_positive_int(obj: dict[str, Any], key: str) -> int:
    value = obj.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PolicyInputError("INVALID_INPUT", f"Field '{key}' must be a positive integer")
    return value


def _reject_unknown(obj: dict[str, Any], allowed: frozenset[str], label: str) -> None:
    extra = set(obj) - allowed
    if extra:
        raise PolicyInputError(
            "INVALID_INPUT",
            f"{label} has undeclared fields: {', '.join(sorted(extra))}",
        )


def parse_principal(raw: dict[str, Any]) -> Principal:
    _reject_unknown(
        raw,
        frozenset({"principal_id", "tenant_id", "roles", "subject_refs", "case_ids"}),
        "Principal",
    )
    roles = raw.get("roles")
    subjects = raw.get("subject_refs")
    cases = raw.get("case_ids")
    if not isinstance(roles, list) or not all(isinstance(r, str) for r in roles):
        raise PolicyInputError("INVALID_INPUT", "roles must be a string array")
    if not isinstance(subjects, list) or not all(isinstance(s, str) for s in subjects):
        raise PolicyInputError("INVALID_INPUT", "subject_refs must be a string array")
    if not isinstance(cases, list) or not all(isinstance(c, str) for c in cases):
        raise PolicyInputError("INVALID_INPUT", "case_ids must be a string array")
    return Principal(
        principal_id=_require_str(raw, "principal_id"),
        tenant_id=_require_str(raw, "tenant_id"),
        roles=tuple(roles),
        subject_refs=tuple(subjects),
        case_ids=tuple(cases),
    )


def parse_evidence(raw: dict[str, Any]) -> Evidence:
    allowed = frozenset(
        {
            "evidence_id",
            "case_id",
            "source",
            "subject_ref",
            "observed_at",
            "expires_at",
            "digest",
            "verification_status",
            "facts",
        }
    )
    _reject_unknown(raw, allowed, "Evidence")
    status = raw.get("verification_status")
    if status not in {"VERIFIED", "UNVERIFIED", "CONFLICTING"}:
        raise PolicyInputError("INVALID_INPUT", "verification_status is invalid")
    facts = raw.get("facts")
    if not isinstance(facts, dict) or "kind" not in facts:
        raise PolicyInputError("INVALID_INPUT", "facts must be a typed object")
    return Evidence(
        evidence_id=_require_str(raw, "evidence_id"),
        case_id=_require_str(raw, "case_id"),
        source=_require_str(raw, "source"),
        subject_ref=_require_str(raw, "subject_ref"),
        observed_at=_require_str(raw, "observed_at"),
        expires_at=_require_str(raw, "expires_at"),
        digest=_require_str(raw, "digest"),
        verification_status=status,  # type: ignore[arg-type]
        facts=facts,
    )


def parse_approval(raw: dict[str, Any]) -> Approval:
    allowed = frozenset(
        {
            "approval_id",
            "action_digest",
            "case_revision",
            "policy_version",
            "decision",
            "reviewer_id",
            "expires_at",
        }
    )
    _reject_unknown(raw, allowed, "Approval")
    decision = raw.get("decision")
    if decision not in {"APPROVE", "REJECT"}:
        raise PolicyInputError("INVALID_INPUT", "decision must be APPROVE or REJECT")
    return Approval(
        approval_id=_require_str(raw, "approval_id"),
        action_digest=_require_str(raw, "action_digest"),
        case_revision=_require_positive_int(raw, "case_revision"),
        policy_version=_require_str(raw, "policy_version"),
        decision=decision,  # type: ignore[arg-type]
        reviewer_id=_require_str(raw, "reviewer_id"),
        expires_at=_require_str(raw, "expires_at"),
    )


def parse_action(raw: dict[str, Any]) -> Action:
    if not isinstance(raw, dict):
        raise PolicyInputError("INVALID_INPUT", "payload must be an object")
    action = raw.get("action")
    if action == "REQUEST_REFUND":
        _reject_unknown(raw, REFUND_ACTION_KEYS, "RefundAction")
        evidence_ids = raw.get("evidence_ids")
        if not isinstance(evidence_ids, list) or not evidence_ids:
            raise PolicyInputError("INVALID_INPUT", "evidence_ids must be a nonempty array")
        if not all(isinstance(i, str) and i for i in evidence_ids):
            raise PolicyInputError("INVALID_INPUT", "evidence_ids must be nonempty strings")
        currency = raw.get("currency")
        if currency != "INR":
            raise PolicyInputError("INVALID_INPUT", "currency must be INR")
        return RefundAction(
            action="REQUEST_REFUND",
            case_id=_require_str(raw, "case_id"),
            case_revision=_require_positive_int(raw, "case_revision"),
            transaction_ref=_require_str(raw, "transaction_ref"),
            amount_minor=_require_positive_int(raw, "amount_minor"),
            currency="INR",
            destination=_require_str(raw, "destination"),
            evidence_ids=tuple(evidence_ids),
            policy_version=_require_str(raw, "policy_version"),
        )
    known = {
        "STATUS_UPDATE",
        "OPEN_DISPUTE",
        "SCHEDULE_RECHECK",
        "SYNC_ORDER",
        "ESCALATE",
    }
    if action not in known:
        raise PolicyInputError("INVALID_INPUT", "Unknown or unsupported action")
    base_keys = {"action", "case_id", "case_revision", "evidence_ids", "policy_version"}
    evidence_ids = raw.get("evidence_ids")
    if not isinstance(evidence_ids, list) or not evidence_ids:
        raise PolicyInputError("INVALID_INPUT", "evidence_ids must be a nonempty array")
    fields = {k: v for k, v in raw.items() if k not in base_keys}
    return GenericAction(
        action=str(action),
        case_id=_require_str(raw, "case_id"),
        case_revision=_require_positive_int(raw, "case_revision"),
        evidence_ids=tuple(evidence_ids),
        policy_version=_require_str(raw, "policy_version"),
        fields=fields,
    )


def parse_policy_request(raw: dict[str, Any]) -> PolicyRequest:
    if not isinstance(raw, dict):
        raise PolicyInputError("INVALID_INPUT", "body must be an object")
    _reject_unknown(raw, frozenset({"payload", "evidence", "approval"}), "PolicyRequest")
    if "payload" not in raw or "evidence" not in raw:
        raise PolicyInputError("INVALID_INPUT", "payload and evidence are required")
    evidence_raw = raw["evidence"]
    if not isinstance(evidence_raw, list):
        raise PolicyInputError("INVALID_INPUT", "evidence must be an array")
    approval = None
    if "approval" in raw:
        if not isinstance(raw["approval"], dict):
            raise PolicyInputError("INVALID_INPUT", "approval must be an object")
        approval = parse_approval(raw["approval"])
    return PolicyRequest(
        payload=parse_action(raw["payload"]),
        evidence=tuple(parse_evidence(item) for item in evidence_raw),
        approval=approval,
    )
