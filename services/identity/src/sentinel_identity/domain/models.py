"""Identity aggregate types (framework-free)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class User:
    user_id: str
    account_type: str  # customer | staff
    email: str
    display_name: str
    status: str  # pending | active | suspended | deactivated
    authz_version: int
    password_hash: str
    created_at: datetime
    updated_at: datetime
    tenant_id: str | None = None  # home tenant hint for seeds
    preferred_language: str = ""

    def to_public(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "account_type": self.account_type,
            "email": self.email,
            "display_name": self.display_name,
            "preferred_language": self.preferred_language,
            "status": self.status,
            "authz_version": self.authz_version,
        }


@dataclass(frozen=True)
class RoleAssignment:
    assignment_id: str
    user_id: str
    tenant_id: str
    role_id: str
    scope_key: str
    status: str  # pending | active | revoked
    granted_by: str | None
    granted_at: datetime
    merchant_ref: str | None = None
    team_id: str | None = None
    revoked_at: datetime | None = None
    grant_review_id: str | None = None

    def to_workspace(self) -> dict[str, Any]:
        return {
            "assignment_id": self.assignment_id,
            "tenant_id": self.tenant_id,
            "role_id": self.role_id,
            "scope_key": self.scope_key,
            "merchant_ref": self.merchant_ref,
            "team_id": self.team_id,
            "status": self.status,
            "grant_review_id": self.grant_review_id,
        }


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    token_hash: str
    user_id: str
    assignment_id: str | None
    authz_version: int
    issued_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    mfa_verified_at: datetime | None = None


@dataclass(frozen=True)
class Invitation:
    invitation_id: str
    work_email: str
    display_name: str
    tenant_id: str
    role_id: str
    scope_key: str
    token_hash: str
    status: str  # pending | accepted | revoked | expired
    invited_by: str
    created_at: datetime
    expires_at: datetime
    idempotency_key: str
    review_state: str = "not_required"  # not_required|awaiting_review|approved|rejected
    privileged_change_id: str | None = None
    merchant_ref: str | None = None
    team_id: str | None = None
    reason: str | None = None
    accepted_at: datetime | None = None
    revoked_at: datetime | None = None
    accepted_user_id: str | None = None

    def to_public(self) -> dict[str, Any]:
        return {
            "invitation_id": self.invitation_id,
            "work_email": self.work_email,
            "display_name": self.display_name,
            "tenant_id": self.tenant_id,
            "role_id": self.role_id,
            "scope_key": self.scope_key,
            "merchant_ref": self.merchant_ref,
            "team_id": self.team_id,
            "status": self.status,
            "review_state": self.review_state,
            "privileged_change_id": self.privileged_change_id,
            "expires_at": self.expires_at.isoformat(),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class PrivilegedChangeRequest:
    change_id: str
    kind: str  # invite | grant
    state: str  # pending | approved | rejected
    maker_user_id: str
    role_id: str
    tenant_id: str
    created_at: datetime
    target_user_id: str | None = None
    invitation_id: str | None = None
    assignment_id: str | None = None
    reviewer_user_id: str | None = None
    decided_at: datetime | None = None
    reason: str | None = None
    decision_reason: str | None = None

    def to_public(self) -> dict[str, Any]:
        return {
            "change_id": self.change_id,
            "kind": self.kind,
            "state": self.state,
            "maker_user_id": self.maker_user_id,
            "reviewer_user_id": self.reviewer_user_id,
            "role_id": self.role_id,
            "tenant_id": self.tenant_id,
            "target_user_id": self.target_user_id,
            "invitation_id": self.invitation_id,
            "assignment_id": self.assignment_id,
            "created_at": self.created_at.isoformat(),
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "reason": self.reason,
            "decision_reason": self.decision_reason,
        }


@dataclass(frozen=True)
class DeliveryOutboxItem:
    """Sandbox invitation delivery row (durable secret + optional acceptance link)."""

    delivery_id: str
    invitation_id: str
    work_email: str
    raw_token: str
    status: str  # pending | delivered
    created_at: datetime
    delivered_at: datetime | None = None
    acceptance_link: str | None = None

    def to_inbox(self) -> dict[str, Any]:
        return {
            "delivery_id": self.delivery_id,
            "invitation_id": self.invitation_id,
            "work_email": self.work_email,
            "subject": "Sentinel staff invitation (sandbox)",
            "acceptance_link": self.acceptance_link,
            "token": self.raw_token,
            "status": self.status,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "evidence_label": "sandbox_inbox",
        }


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    actor_user_id: str | None
    action: str
    target_type: str
    target_id: str
    tenant_id: str | None
    at: datetime
    details: dict[str, Any] = field(default_factory=dict)
    request_id: str = "request-local"

    def to_public(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "actor_user_id": self.actor_user_id,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "tenant_id": self.tenant_id,
            "at": self.at.isoformat(),
            "details": self.details,
            "request_id": self.request_id,
        }
