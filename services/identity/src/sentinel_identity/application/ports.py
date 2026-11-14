"""Narrow ports for identity persistence and time."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from ..domain.models import (
    AuditEvent,
    DeliveryOutboxItem,
    Invitation,
    Notification,
    PrivilegedChangeRequest,
    RoleAssignment,
    SessionRecord,
    User,
)


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdentityStore(Protocol):
    def create_user(self, user: User) -> User: ...

    def get_user(self, user_id: str) -> User | None: ...

    def get_user_by_email(self, email: str) -> User | None: ...

    def save_user(self, user: User) -> User: ...

    def list_users(self, *, tenant_id: str | None = None) -> tuple[User, ...]: ...

    def create_assignment(self, assignment: RoleAssignment) -> RoleAssignment: ...

    def get_assignment(self, assignment_id: str) -> RoleAssignment | None: ...

    def save_assignment(self, assignment: RoleAssignment) -> RoleAssignment: ...

    def list_assignments(self, user_id: str) -> tuple[RoleAssignment, ...]: ...

    def list_assignments_for_merchant(
        self, *, tenant_id: str, merchant_ref: str
    ) -> tuple[RoleAssignment, ...]: ...

    def create_session(self, session: SessionRecord) -> SessionRecord: ...

    def get_session_by_token_hash(self, token_hash: str) -> SessionRecord | None: ...

    def save_session(self, session: SessionRecord) -> SessionRecord: ...

    def revoke_sessions_for_user(self, user_id: str, *, at: datetime) -> int: ...

    def create_invitation(self, invitation: Invitation) -> Invitation: ...

    def get_invitation(self, invitation_id: str) -> Invitation | None: ...

    def get_invitation_by_idempotency(self, key: str) -> Invitation | None: ...

    def get_invitation_by_token_hash(self, token_hash: str) -> Invitation | None: ...

    def save_invitation(self, invitation: Invitation) -> Invitation: ...

    def list_invitations(self, *, tenant_id: str | None = None) -> tuple[Invitation, ...]: ...

    def consume_invitation_with_assignment(
        self,
        *,
        token_hash: str,
        user: User,
        assignment: RoleAssignment,
        at: datetime,
    ) -> Invitation:
        """Claim pending invite then write user+assignment atomically."""
        ...

    def create_privileged_change(
        self, change: PrivilegedChangeRequest
    ) -> PrivilegedChangeRequest: ...

    def get_privileged_change(self, change_id: str) -> PrivilegedChangeRequest | None: ...

    def save_privileged_change(
        self, change: PrivilegedChangeRequest
    ) -> PrivilegedChangeRequest: ...

    def apply_authz_bundle(
        self,
        *,
        user: User,
        assignment: RoleAssignment,
        assignment_mode: str,
        at: datetime,
        revoke_sessions: bool,
        change: PrivilegedChangeRequest | None = None,
        invitation: Invitation | None = None,
    ) -> None:
        """Atomic grant/revoke/activate: assignment + authz_version + optional session revoke."""
        ...

    def record_delivery_secret(
        self, invitation_id: str, raw_token: str, *, work_email: str
    ) -> None:
        """Persist invite plaintext for sandbox delivery outbox (not admin API)."""
        ...

    def peek_delivery_secret(self, invitation_id: str) -> str | None: ...

    def list_pending_deliveries(self) -> tuple[DeliveryOutboxItem, ...]: ...

    def mark_delivery_delivered(
        self, delivery_id: str, *, acceptance_link: str, at: datetime
    ) -> None: ...

    def list_sandbox_inbox(
        self, *, work_email: str | None = None
    ) -> tuple[DeliveryOutboxItem, ...]: ...

    def create_notification(self, notification: Notification) -> Notification: ...

    def get_notification(self, notification_id: str) -> Notification | None: ...

    def save_notification(self, notification: Notification) -> Notification: ...

    def list_notifications(self, user_id: str, *, limit: int = 50) -> tuple[Notification, ...]: ...

    def append_audit(self, event: AuditEvent) -> AuditEvent: ...

    def list_audit(self, *, limit: int = 100) -> tuple[AuditEvent, ...]: ...
