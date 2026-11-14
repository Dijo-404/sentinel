"""Wire-aligned types for merchant-teams.v1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CONTRACT_VERSION = "sentinel.task-contracts.v1"

STAFF_ROLES = frozenset({"viewer", "operator", "approver", "admin"})

# Platform / identity-owned authorities. Merchant-teams projects membership only;
# it must never mint these as local staff roles.
PLATFORM_AUTHORITY_ROLES = frozenset(
    {
        "customer",
        "merchant",
        "supervisor",
        "risk_officer",
        "platform_admin",
        "workflow",
        "dispatcher",
        "verifier",
        "sandbox-admin",
    }
)


@dataclass(frozen=True, slots=True)
class Principal:
    principal_id: str
    tenant_id: str
    roles: tuple[str, ...]
    subject_refs: tuple[str, ...]
    case_ids: tuple[str, ...]

    def allows_merchant(self, merchant_ref: str) -> bool:
        if "*" in self.subject_refs:
            return True
        return merchant_ref in self.subject_refs

    def allows_case(self, case_id: str) -> bool:
        if "*" in self.case_ids:
            return True
        return case_id in self.case_ids


@dataclass(frozen=True, slots=True)
class MerchantStaff:
    staff_id: str
    tenant_id: str
    merchant_ref: str
    display_name: str
    roles: tuple[str, ...]
    active: bool
    approval_limit_minor: int | None = None
    currency: str | None = None

    def to_wire(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "staff_id": self.staff_id,
            "tenant_id": self.tenant_id,
            "merchant_ref": self.merchant_ref,
            "display_name": self.display_name,
            "roles": list(self.roles),
            "active": self.active,
        }
        if self.approval_limit_minor is not None:
            body["approval_limit_minor"] = self.approval_limit_minor
        if self.currency is not None:
            body["currency"] = self.currency
        return body

    @classmethod
    def from_wire(cls, body: dict[str, Any]) -> MerchantStaff:
        return cls(
            staff_id=str(body["staff_id"]),
            tenant_id=str(body["tenant_id"]),
            merchant_ref=str(body["merchant_ref"]),
            display_name=str(body["display_name"]),
            roles=tuple(str(r) for r in body["roles"]),
            active=bool(body["active"]),
            approval_limit_minor=(
                int(body["approval_limit_minor"]) if "approval_limit_minor" in body else None
            ),
            currency=str(body["currency"]) if "currency" in body else None,
        )


@dataclass(frozen=True, slots=True)
class StaffActivity:
    event_id: str
    staff_id: str
    at: str
    kind: str
    subject_ref: str
    summary: str

    def to_wire(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "staff_id": self.staff_id,
            "at": self.at,
            "kind": self.kind,
            "subject_ref": self.subject_ref,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class CaseSnapshot:
    case_id: str
    revision: int
    status: str
    contract_version: str


@dataclass(frozen=True, slots=True)
class IdentityMembership:
    """Authoritative merchant membership row from identity.v1 (projection source)."""

    membership_id: str
    assignment_id: str
    user_id: str
    tenant_id: str
    merchant_ref: str
    display_name: str
    subroles: tuple[str, ...]
    status: str

    def to_wire(self) -> dict[str, Any]:
        return {
            "membership_id": self.membership_id,
            "assignment_id": self.assignment_id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "merchant_ref": self.merchant_ref,
            "display_name": self.display_name,
            "subroles": list(self.subroles),
            "status": self.status,
        }

    @classmethod
    def from_wire(cls, body: dict[str, Any]) -> IdentityMembership:
        return cls(
            membership_id=str(body["membership_id"]),
            assignment_id=str(body["assignment_id"]),
            user_id=str(body["user_id"]),
            tenant_id=str(body["tenant_id"]),
            merchant_ref=str(body["merchant_ref"]),
            display_name=str(body["display_name"]),
            subroles=tuple(str(r) for r in body["subroles"]),
            status=str(body["status"]),
        )


@dataclass(frozen=True, slots=True)
class AdvisoryLimitResult:
    """Advisory-only check. Never an Approval or Reservation."""

    staff_id: str
    amount_minor: int
    currency: str
    within_advisory_limit: bool
    advisory: bool
    authorizes_ledger_or_provider: bool
    approval_id: None
    reservation_id: None

    def to_wire(self) -> dict[str, Any]:
        return {
            "staff_id": self.staff_id,
            "amount_minor": self.amount_minor,
            "currency": self.currency,
            "within_advisory_limit": self.within_advisory_limit,
            "advisory": self.advisory,
            "authorizes_ledger_or_provider": self.authorizes_ledger_or_provider,
            "approval_id": self.approval_id,
            "reservation_id": self.reservation_id,
        }
