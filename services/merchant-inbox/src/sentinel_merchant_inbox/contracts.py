"""Task-local typed snapshot of merchant-inbox.v1 wire types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

CONTRACT_VERSION = "sentinel.task-contracts.v1"
CONTRACT_SHA256 = "0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb"
PORT = "merchant-inbox.v1"
COMPONENT = "merchant-inbox"

ExceptionKind = Literal["PAID_UNFULFILLED", "UNMATCHED_PAYMENT", "PENDING_REFUND"]
ExceptionStatus = Literal["OPEN", "ASSIGNED", "ESCALATED", "CLOSED"]
KINDS = frozenset({"PAID_UNFULFILLED", "UNMATCHED_PAYMENT", "PENDING_REFUND"})
STATUSES = frozenset({"OPEN", "ASSIGNED", "ESCALATED", "CLOSED"})
MERCHANT_ROLES = frozenset({"operator", "supervisor"})


class InboxInputError(ValueError):
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

    def is_merchant_staff(self) -> bool:
        return bool(MERCHANT_ROLES.intersection(self.roles))

    def allows_case(self, case_id: str) -> bool:
        if "*" in self.case_ids:
            return True
        return case_id in self.case_ids


@dataclass(frozen=True)
class MerchantBinding:
    principal: Principal
    merchant_refs: tuple[str, ...]

    def allows_merchant(self, merchant_ref: str) -> bool:
        if "*" in self.merchant_refs:
            return True
        return merchant_ref in self.merchant_refs


@dataclass
class ExceptionItem:
    item_id: str
    tenant_id: str
    merchant_ref: str
    kind: ExceptionKind
    amount_minor: int
    currency: str
    status: ExceptionStatus
    notes: list[str] = field(default_factory=list)
    case_id: str | None = None
    transaction_ref: str | None = None
    assignee: str | None = None

    def as_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "item_id": self.item_id,
            "tenant_id": self.tenant_id,
            "merchant_ref": self.merchant_ref,
            "kind": self.kind,
            "amount_minor": self.amount_minor,
            "currency": self.currency,
            "notes": list(self.notes),
            "status": self.status,
        }
        if self.case_id is not None:
            body["case_id"] = self.case_id
        if self.transaction_ref is not None:
            body["transaction_ref"] = self.transaction_ref
        if self.assignee is not None:
            body["assignee"] = self.assignee
        return body


def parse_principal(raw: dict[str, Any]) -> Principal:
    required = ("principal_id", "tenant_id", "roles", "subject_refs", "case_ids")
    extra = set(raw) - set(required)
    if extra:
        raise InboxInputError("INVALID_INPUT", f"Undeclared principal fields: {sorted(extra)}")
    for key in required:
        if key not in raw:
            raise InboxInputError("INVALID_INPUT", f"Missing principal field: {key}")
    if not isinstance(raw["principal_id"], str) or not raw["principal_id"]:
        raise InboxInputError("INVALID_INPUT", "principal_id must be a nonempty string")
    if not isinstance(raw["tenant_id"], str) or not raw["tenant_id"]:
        raise InboxInputError("INVALID_INPUT", "tenant_id must be a nonempty string")
    if not isinstance(raw["roles"], list) or not all(isinstance(r, str) for r in raw["roles"]):
        raise InboxInputError("INVALID_INPUT", "roles must be a string array")
    if not isinstance(raw["subject_refs"], list) or not all(
        isinstance(s, str) for s in raw["subject_refs"]
    ):
        raise InboxInputError("INVALID_INPUT", "subject_refs must be a string array")
    if not isinstance(raw["case_ids"], list) or not all(
        isinstance(c, str) for c in raw["case_ids"]
    ):
        raise InboxInputError("INVALID_INPUT", "case_ids must be a string array")
    return Principal(
        principal_id=raw["principal_id"],
        tenant_id=raw["tenant_id"],
        roles=tuple(raw["roles"]),
        subject_refs=tuple(raw["subject_refs"]),
        case_ids=tuple(raw["case_ids"]),
    )


def parse_exception_item(raw: dict[str, Any]) -> ExceptionItem:
    required = {
        "item_id",
        "tenant_id",
        "merchant_ref",
        "kind",
        "amount_minor",
        "currency",
        "notes",
        "status",
    }
    optional = {"case_id", "transaction_ref", "assignee"}
    extra = set(raw) - required - optional
    if extra:
        raise InboxInputError("INVALID_INPUT", f"Undeclared exception fields: {sorted(extra)}")
    for key in required:
        if key not in raw:
            raise InboxInputError("INVALID_INPUT", f"Missing exception field: {key}")
    if raw["kind"] not in KINDS:
        raise InboxInputError("INVALID_INPUT", f"Unknown kind: {raw['kind']}")
    if raw["status"] not in STATUSES:
        raise InboxInputError("INVALID_INPUT", f"Unknown status: {raw['status']}")
    if not isinstance(raw["amount_minor"], int) or isinstance(raw["amount_minor"], bool):
        raise InboxInputError("INVALID_INPUT", "amount_minor must be an integer")
    if raw["amount_minor"] < 0:
        raise InboxInputError("INVALID_INPUT", "amount_minor must be >= 0")
    if not isinstance(raw["currency"], str) or not raw["currency"]:
        raise InboxInputError("INVALID_INPUT", "currency must be a nonempty string")
    if not isinstance(raw["notes"], list) or not all(isinstance(n, str) for n in raw["notes"]):
        raise InboxInputError("INVALID_INPUT", "notes must be a string array")
    case_id = raw.get("case_id")
    transaction_ref = raw.get("transaction_ref")
    assignee = raw.get("assignee")
    if case_id is not None and (not isinstance(case_id, str) or not case_id):
        raise InboxInputError("INVALID_INPUT", "case_id must be a nonempty string when present")
    if transaction_ref is not None and (
        not isinstance(transaction_ref, str) or not transaction_ref
    ):
        raise InboxInputError(
            "INVALID_INPUT", "transaction_ref must be a nonempty string when present"
        )
    if assignee is not None and (not isinstance(assignee, str) or not assignee):
        raise InboxInputError("INVALID_INPUT", "assignee must be a nonempty string when present")
    return ExceptionItem(
        item_id=str(raw["item_id"]),
        tenant_id=str(raw["tenant_id"]),
        merchant_ref=str(raw["merchant_ref"]),
        kind=raw["kind"],
        amount_minor=raw["amount_minor"],
        currency=raw["currency"],
        status=raw["status"],
        notes=list(raw["notes"]),
        case_id=case_id,
        transaction_ref=transaction_ref,
        assignee=assignee,
    )
