"""Task-local typed snapshot of merchant-sla.v1 and case-api.v1 wire types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

CONTRACT_VERSION = "sentinel.task-contracts.v1"
CONTRACT_SHA256 = "0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb"
PORT = "merchant-sla.v1"
COMPONENT = "merchant-sla"

TaskStatus = Literal["OPEN", "IN_PROGRESS", "ESCALATED", "DONE"]
SlaTarget = Literal["respond", "resolve"]
CaseStatus = Literal[
    "RECEIVED",
    "NEEDS_INPUT",
    "INVESTIGATING",
    "RECONCILING",
    "PLANNING",
    "POLICY_CHECK",
    "WAITING_APPROVAL",
    "EXECUTING",
    "VERIFYING",
    "WAITING_EXTERNAL",
    "ESCALATED",
    "VERIFIED_RESOLVED",
    "CLOSED_NO_ACTION",
]

TASK_STATUSES: frozenset[str] = frozenset({"OPEN", "IN_PROGRESS", "ESCALATED", "DONE"})
RESOLVED_CASE_STATUSES: frozenset[str] = frozenset({"VERIFIED_RESOLVED", "CLOSED_NO_ACTION"})


class SlaInputError(ValueError):
    """Malformed request; safe for API 422 mapping."""

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
    merchant_refs: tuple[str, ...]

    def allows_case(self, case_id: str) -> bool:
        if "*" in self.case_ids:
            return True
        return case_id in self.case_ids

    def allows_merchant(self, merchant_ref: str) -> bool:
        if "*" in self.merchant_refs:
            return True
        return merchant_ref in self.merchant_refs


@dataclass(frozen=True)
class CaseRecord:
    case_id: str
    revision: int
    status: str
    language: str
    intent: str
    evidence_ids: tuple[str, ...]
    contract_version: str
    tenant_id: str | None = None
    merchant_ref: str | None = None
    opened_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "contract_version": self.contract_version,
            "case_id": self.case_id,
            "revision": self.revision,
            "status": self.status,
            "language": self.language,
            "intent": self.intent,
            "evidence_ids": list(self.evidence_ids),
        }
        if self.tenant_id is not None:
            body["tenant_id"] = self.tenant_id
        if self.merchant_ref is not None:
            body["merchant_ref"] = self.merchant_ref
        if self.opened_at is not None:
            body["opened_at"] = self.opened_at
        return body


@dataclass(frozen=True)
class SlaPolicy:
    policy_id: str
    tenant_id: str
    merchant_ref: str
    respond_within_seconds: int
    resolve_within_seconds: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "tenant_id": self.tenant_id,
            "merchant_ref": self.merchant_ref,
            "respond_within_seconds": self.respond_within_seconds,
            "resolve_within_seconds": self.resolve_within_seconds,
        }


@dataclass(frozen=True)
class SlaTask:
    task_id: str
    case_id: str
    due_at: str
    overdue: bool
    status: TaskStatus
    assignee: str | None = None
    follow_up_at: str | None = None
    policy_id: str | None = None
    tenant_id: str | None = None
    merchant_ref: str | None = None
    case_status: str | None = None
    financially_resolved: bool = False

    def as_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "task_id": self.task_id,
            "case_id": self.case_id,
            "due_at": self.due_at,
            "overdue": self.overdue,
            "status": self.status,
        }
        if self.assignee is not None:
            body["assignee"] = self.assignee
        if self.follow_up_at is not None:
            body["follow_up_at"] = self.follow_up_at
        if self.policy_id is not None:
            body["policy_id"] = self.policy_id
        if self.tenant_id is not None:
            body["tenant_id"] = self.tenant_id
        if self.merchant_ref is not None:
            body["merchant_ref"] = self.merchant_ref
        if self.case_status is not None:
            body["case_status"] = self.case_status
        body["financially_resolved"] = self.financially_resolved
        return body


def parse_principal(raw: dict[str, Any]) -> Principal:
    try:
        roles = tuple(str(r) for r in raw["roles"])
        subject_refs = tuple(str(s) for s in raw.get("subject_refs", ()))
        case_ids = tuple(str(c) for c in raw.get("case_ids", ()))
        merchant_refs = tuple(str(m) for m in raw.get("merchant_refs", ()))
        return Principal(
            principal_id=str(raw["principal_id"]),
            tenant_id=str(raw["tenant_id"]),
            roles=roles,
            subject_refs=subject_refs,
            case_ids=case_ids,
            merchant_refs=merchant_refs,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SlaInputError("INVALID_CONFIG", f"invalid principal: {exc}") from exc


def parse_case(raw: Any) -> CaseRecord:
    if not isinstance(raw, dict):
        raise SlaInputError("MALFORMED", "case body must be an object")
    required = (
        "case_id",
        "revision",
        "status",
        "language",
        "intent",
        "evidence_ids",
        "contract_version",
    )
    missing = [k for k in required if k not in raw]
    if missing:
        raise SlaInputError("MALFORMED", f"case missing fields: {', '.join(missing)}")
    revision = raw["revision"]
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise SlaInputError("MALFORMED", "case.revision must be a positive integer")
    evidence_ids = raw["evidence_ids"]
    if not isinstance(evidence_ids, list) or not all(isinstance(x, str) for x in evidence_ids):
        raise SlaInputError("MALFORMED", "case.evidence_ids must be a string list")
    return CaseRecord(
        case_id=str(raw["case_id"]),
        revision=revision,
        status=str(raw["status"]),
        language=str(raw["language"]),
        intent=str(raw["intent"]),
        evidence_ids=tuple(evidence_ids),
        contract_version=str(raw["contract_version"]),
        tenant_id=str(raw["tenant_id"]) if raw.get("tenant_id") is not None else None,
        merchant_ref=str(raw["merchant_ref"]) if raw.get("merchant_ref") is not None else None,
        opened_at=str(raw["opened_at"]) if raw.get("opened_at") is not None else None,
    )


def parse_policy_body(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise SlaInputError("INVALID_INPUT", "body must be an object")
    for key in ("tenant_id", "merchant_ref"):
        if key not in raw or not isinstance(raw[key], str) or not raw[key]:
            raise SlaInputError("INVALID_INPUT", f"{key} must be a nonempty string")
    for key in ("respond_within_seconds", "resolve_within_seconds"):
        value = raw.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise SlaInputError("INVALID_INPUT", f"{key} must be a positive integer")
    if raw["resolve_within_seconds"] < raw["respond_within_seconds"]:
        raise SlaInputError(
            "INVALID_INPUT",
            "resolve_within_seconds must be >= respond_within_seconds",
        )
    policy_id = raw.get("policy_id")
    if policy_id is not None and (not isinstance(policy_id, str) or not policy_id):
        raise SlaInputError("INVALID_INPUT", "policy_id must be a nonempty string when set")
    return {
        "policy_id": policy_id,
        "tenant_id": raw["tenant_id"],
        "merchant_ref": raw["merchant_ref"],
        "respond_within_seconds": raw["respond_within_seconds"],
        "resolve_within_seconds": raw["resolve_within_seconds"],
    }


def parse_create_task_body(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise SlaInputError("INVALID_INPUT", "body must be an object")
    for key in ("case_id", "policy_id"):
        if key not in raw or not isinstance(raw[key], str) or not raw[key]:
            raise SlaInputError("INVALID_INPUT", f"{key} must be a nonempty string")
    target = raw.get("target", "resolve")
    if target not in ("respond", "resolve"):
        raise SlaInputError("INVALID_INPUT", "target must be respond or resolve")
    assignee = raw.get("assignee")
    if assignee is not None and (not isinstance(assignee, str) or not assignee):
        raise SlaInputError("INVALID_INPUT", "assignee must be a nonempty string when set")
    return {
        "case_id": raw["case_id"],
        "policy_id": raw["policy_id"],
        "target": target,
        "assignee": assignee,
    }
