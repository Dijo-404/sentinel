"""In-process identity store for fixture mode and unit tests."""

from __future__ import annotations

import uuid
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from threading import RLock

from ..application.errors import ConflictError, ForbiddenError
from ..domain.models import (
    AuditEvent,
    AuthChallenge,
    AuthDeliveryLogEntry,
    DeliveryOutboxItem,
    Invitation,
    Notification,
    PrivilegedChangeRequest,
    RoleAssignment,
    SessionRecord,
    User,
)


class MemoryIdentityStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self.users: dict[str, User] = {}
        self.users_by_email: dict[str, str] = {}
        self.assignments: dict[str, RoleAssignment] = {}
        self.sessions: dict[str, SessionRecord] = {}
        self.sessions_by_hash: dict[str, str] = {}
        self.invitations: dict[str, Invitation] = {}
        self.invitations_by_idem: dict[str, str] = {}
        self.invitations_by_hash: dict[str, str] = {}
        self.privileged_changes: dict[str, PrivilegedChangeRequest] = {}
        self.audit: list[AuditEvent] = []
        self.notifications: dict[str, Notification] = {}
        self.auth_challenges: dict[str, AuthChallenge] = {}
        self.auth_delivery_log: dict[str, AuthDeliveryLogEntry] = {}
        # In-process only; never written to durable delivery log rows.
        self._sandbox_codes: dict[str, str] = {}
        self._delivery_outbox: dict[str, DeliveryOutboxItem] = {}
        self._delivery_by_invitation: dict[str, str] = {}

    def create_user(self, user: User) -> User:
        with self._lock:
            if user.user_id in self.users:
                raise ValueError("user_id already exists")
            if user.email in self.users_by_email:
                raise ValueError("email already exists")
            self.users[user.user_id] = user
            self.users_by_email[user.email] = user.user_id
            return user

    def get_user(self, user_id: str) -> User | None:
        return self.users.get(user_id)

    def get_user_by_email(self, email: str) -> User | None:
        uid = self.users_by_email.get(email)
        return self.users.get(uid) if uid else None

    def save_user(self, user: User) -> User:
        with self._lock:
            prev = self.users.get(user.user_id)
            if prev and prev.email != user.email:
                self.users_by_email.pop(prev.email, None)
            self.users[user.user_id] = user
            self.users_by_email[user.email] = user.user_id
            return user

    def list_users(self, *, tenant_id: str | None = None) -> tuple[User, ...]:
        rows = list(self.users.values())
        if tenant_id is not None:
            rows = [u for u in rows if u.tenant_id == tenant_id]
        return tuple(sorted(rows, key=lambda u: u.email))

    def create_assignment(self, assignment: RoleAssignment) -> RoleAssignment:
        with self._lock:
            self.assignments[assignment.assignment_id] = assignment
            return assignment

    def get_assignment(self, assignment_id: str) -> RoleAssignment | None:
        return self.assignments.get(assignment_id)

    def save_assignment(self, assignment: RoleAssignment) -> RoleAssignment:
        with self._lock:
            self.assignments[assignment.assignment_id] = assignment
            return assignment

    def list_assignments(self, user_id: str) -> tuple[RoleAssignment, ...]:
        rows = [a for a in self.assignments.values() if a.user_id == user_id]
        return tuple(sorted(rows, key=lambda a: a.granted_at.isoformat()))

    def list_assignments_for_merchant(
        self, *, tenant_id: str, merchant_ref: str
    ) -> tuple[RoleAssignment, ...]:
        rows = [
            a
            for a in self.assignments.values()
            if a.tenant_id == tenant_id and a.merchant_ref == merchant_ref
        ]
        return tuple(sorted(rows, key=lambda a: a.granted_at.isoformat()))

    def create_session(self, session: SessionRecord) -> SessionRecord:
        with self._lock:
            self.sessions[session.session_id] = session
            self.sessions_by_hash[session.token_hash] = session.session_id
            return session

    def get_session_by_token_hash(self, token_hash: str) -> SessionRecord | None:
        sid = self.sessions_by_hash.get(token_hash)
        return self.sessions.get(sid) if sid else None

    def save_session(self, session: SessionRecord) -> SessionRecord:
        with self._lock:
            self.sessions[session.session_id] = session
            self.sessions_by_hash[session.token_hash] = session.session_id
            return session

    def revoke_sessions_for_user(self, user_id: str, *, at: datetime) -> int:
        with self._lock:
            return self._revoke_sessions_unlocked(user_id, at=at)

    def _revoke_sessions_unlocked(self, user_id: str, *, at: datetime) -> int:
        count = 0
        for sid, session in list(self.sessions.items()):
            if session.user_id == user_id and session.revoked_at is None:
                self.sessions[sid] = SessionRecord(
                    session_id=session.session_id,
                    token_hash=session.token_hash,
                    user_id=session.user_id,
                    assignment_id=session.assignment_id,
                    authz_version=session.authz_version,
                    issued_at=session.issued_at,
                    expires_at=session.expires_at,
                    revoked_at=at,
                    mfa_verified_at=session.mfa_verified_at,
                )
                count += 1
        return count

    def create_invitation(self, invitation: Invitation) -> Invitation:
        with self._lock:
            self.invitations[invitation.invitation_id] = invitation
            self.invitations_by_idem[invitation.idempotency_key] = invitation.invitation_id
            self.invitations_by_hash[invitation.token_hash] = invitation.invitation_id
            return invitation

    def get_invitation(self, invitation_id: str) -> Invitation | None:
        return self.invitations.get(invitation_id)

    def get_invitation_by_idempotency(self, key: str) -> Invitation | None:
        iid = self.invitations_by_idem.get(key)
        return self.invitations.get(iid) if iid else None

    def get_invitation_by_token_hash(self, token_hash: str) -> Invitation | None:
        iid = self.invitations_by_hash.get(token_hash)
        return self.invitations.get(iid) if iid else None

    def save_invitation(self, invitation: Invitation) -> Invitation:
        with self._lock:
            self.invitations[invitation.invitation_id] = invitation
            self.invitations_by_idem[invitation.idempotency_key] = invitation.invitation_id
            self.invitations_by_hash[invitation.token_hash] = invitation.invitation_id
            return invitation

    def list_invitations(self, *, tenant_id: str | None = None) -> tuple[Invitation, ...]:
        rows = list(self.invitations.values())
        if tenant_id is not None:
            rows = [i for i in rows if i.tenant_id == tenant_id]
        return tuple(sorted(rows, key=lambda i: i.created_at.isoformat(), reverse=True))

    def consume_invitation_with_assignment(
        self,
        *,
        token_hash: str,
        user: User,
        assignment: RoleAssignment,
        at: datetime,
    ) -> Invitation:
        with self._lock:
            iid = self.invitations_by_hash.get(token_hash)
            invitation = self.invitations.get(iid) if iid else None
            if invitation is None:
                raise ForbiddenError("Invitation denied")
            if invitation.status != "pending":
                raise ConflictError("Invitation is no longer pending")
            if invitation.review_state == "awaiting_review":
                raise ForbiddenError("Invitation awaiting independent review")
            if invitation.review_state == "rejected":
                raise ForbiddenError("Invitation rejected")
            if invitation.expires_at <= at:
                self.invitations[invitation.invitation_id] = replace(invitation, status="expired")
                raise ForbiddenError("Invitation expired")
            claimed = replace(
                invitation,
                status="accepted",
                accepted_at=at,
                accepted_user_id=user.user_id,
            )
            self.invitations[claimed.invitation_id] = claimed
            prev = self.users.get(user.user_id)
            if prev is None:
                if user.email in self.users_by_email:
                    raise ConflictError("Account already exists")
                self.users[user.user_id] = user
                self.users_by_email[user.email] = user.user_id
            else:
                self.users[user.user_id] = user
                self.users_by_email[user.email] = user.user_id
            self.assignments[assignment.assignment_id] = assignment
            return claimed

    def create_privileged_change(self, change: PrivilegedChangeRequest) -> PrivilegedChangeRequest:
        with self._lock:
            self.privileged_changes[change.change_id] = change
            return change

    def get_privileged_change(self, change_id: str) -> PrivilegedChangeRequest | None:
        return self.privileged_changes.get(change_id)

    def save_privileged_change(self, change: PrivilegedChangeRequest) -> PrivilegedChangeRequest:
        with self._lock:
            self.privileged_changes[change.change_id] = change
            return change

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
        with self._lock:
            if assignment_mode == "create":
                self.assignments[assignment.assignment_id] = assignment
            elif assignment_mode == "save":
                self.assignments[assignment.assignment_id] = assignment
            else:
                raise ValueError(f"unknown assignment_mode {assignment_mode!r}")
            self.users[user.user_id] = user
            self.users_by_email[user.email] = user.user_id
            if change is not None:
                self.privileged_changes[change.change_id] = change
            if invitation is not None:
                self.invitations[invitation.invitation_id] = invitation
                self.invitations_by_idem[invitation.idempotency_key] = invitation.invitation_id
                self.invitations_by_hash[invitation.token_hash] = invitation.invitation_id
            if revoke_sessions:
                self._revoke_sessions_unlocked(user.user_id, at=at)

    def record_delivery_secret(
        self, invitation_id: str, raw_token: str, *, work_email: str
    ) -> None:
        with self._lock:
            existing_id = self._delivery_by_invitation.get(invitation_id)
            if existing_id is not None:
                return
            delivery_id = str(uuid.uuid4())
            invitation = self.invitations.get(invitation_id)
            if invitation is None:
                raise KeyError(f"invitation {invitation_id} not found")
            item = DeliveryOutboxItem(
                delivery_id=delivery_id,
                invitation_id=invitation_id,
                work_email=work_email,
                raw_token=raw_token,
                status="pending",
                created_at=invitation.created_at,
            )
            self._delivery_outbox[delivery_id] = item
            self._delivery_by_invitation[invitation_id] = delivery_id

    def peek_delivery_secret(self, invitation_id: str) -> str | None:
        delivery_id = self._delivery_by_invitation.get(invitation_id)
        if delivery_id is None:
            return None
        item = self._delivery_outbox.get(delivery_id)
        return item.raw_token if item is not None else None

    def list_pending_deliveries(self) -> tuple[DeliveryOutboxItem, ...]:
        rows = [i for i in self._delivery_outbox.values() if i.status == "pending"]
        rows.sort(key=lambda i: i.created_at)
        return tuple(rows)

    def mark_delivery_delivered(
        self, delivery_id: str, *, acceptance_link: str, at: datetime
    ) -> None:
        with self._lock:
            item = self._delivery_outbox.get(delivery_id)
            if item is None:
                raise KeyError(delivery_id)
            if item.status == "delivered":
                return
            self._delivery_outbox[delivery_id] = replace(
                item,
                status="delivered",
                delivered_at=at,
                acceptance_link=acceptance_link,
            )

    def list_sandbox_inbox(
        self, *, work_email: str | None = None
    ) -> tuple[DeliveryOutboxItem, ...]:
        rows = [i for i in self._delivery_outbox.values() if i.status == "delivered"]
        if work_email is not None:
            needle = work_email.strip().lower()
            rows = [i for i in rows if i.work_email.lower() == needle]
        rows.sort(key=lambda i: i.delivered_at or i.created_at, reverse=True)
        return tuple(rows)

    def create_notification(self, notification: Notification) -> Notification:
        with self._lock:
            if notification.notification_id in self.notifications:
                raise ValueError("notification_id already exists")
            self.notifications[notification.notification_id] = notification
            return notification

    def get_notification(self, notification_id: str) -> Notification | None:
        return self.notifications.get(notification_id)

    def save_notification(self, notification: Notification) -> Notification:
        with self._lock:
            self.notifications[notification.notification_id] = notification
            return notification

    def list_notifications(self, user_id: str, *, limit: int = 50) -> tuple[Notification, ...]:
        rows = [n for n in self.notifications.values() if n.user_id == user_id]
        rows.sort(key=lambda n: n.created_at.isoformat(), reverse=True)
        return tuple(rows[:limit])

    def create_auth_challenge(self, challenge: AuthChallenge) -> AuthChallenge:
        with self._lock:
            if challenge.challenge_id in self.auth_challenges:
                raise ValueError("challenge_id already exists")
            self.auth_challenges[challenge.challenge_id] = challenge
            return challenge

    def save_auth_challenge(self, challenge: AuthChallenge) -> AuthChallenge:
        with self._lock:
            self.auth_challenges[challenge.challenge_id] = challenge
            return challenge

    def get_active_auth_challenge(
        self, *, user_id: str, challenge_type: str, at: datetime
    ) -> AuthChallenge | None:
        rows = [
            c
            for c in self.auth_challenges.values()
            if c.user_id == user_id
            and c.challenge_type == challenge_type
            and c.consumed_at is None
            and c.expires_at > at
        ]
        if not rows:
            return None
        rows.sort(key=lambda c: c.created_at.isoformat(), reverse=True)
        return rows[0]

    def try_consume_auth_challenge(
        self, challenge_id: str, *, at: datetime
    ) -> AuthChallenge | None:
        with self._lock:
            challenge = self.auth_challenges.get(challenge_id)
            if challenge is None or challenge.consumed_at is not None or challenge.expires_at <= at:
                return None
            updated = replace(challenge, consumed_at=at)
            self.auth_challenges[challenge_id] = updated
            return updated

    def record_auth_challenge_failure(
        self, challenge_id: str, *, at: datetime, max_attempts: int
    ) -> AuthChallenge | None:
        with self._lock:
            challenge = self.auth_challenges.get(challenge_id)
            if challenge is None or challenge.consumed_at is not None or challenge.expires_at <= at:
                return None
            attempts = challenge.attempt_count + 1
            consumed_at = at if attempts >= max_attempts else None
            updated = replace(challenge, attempt_count=attempts, consumed_at=consumed_at)
            self.auth_challenges[challenge_id] = updated
            return updated

    def append_auth_delivery(
        self,
        *,
        challenge_id: str,
        user_id: str,
        destination: str,
        purpose: str,
        at: datetime,
        raw_code: str = "",
    ) -> AuthDeliveryLogEntry:
        with self._lock:
            entry = AuthDeliveryLogEntry(
                log_id=str(uuid.uuid4()),
                channel="loopback",
                destination=destination,
                purpose=purpose,
                challenge_id=challenge_id,
                user_id=user_id,
                created_at=at,
            )
            self.auth_delivery_log[entry.log_id] = entry
            if raw_code:
                self._sandbox_codes[challenge_id] = raw_code
            return entry

    def peek_auth_sandbox_code(self, *, user_id: str, purpose: str) -> str | None:
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        with self._lock:
            rows = [
                e
                for e in self.auth_delivery_log.values()
                if e.user_id == user_id and e.purpose == purpose
            ]
            rows.sort(key=lambda e: e.created_at.isoformat(), reverse=True)
            for entry in rows:
                code = self._sandbox_codes.get(entry.challenge_id)
                if not code:
                    continue
                challenge = self.auth_challenges.get(entry.challenge_id)
                if challenge is None:
                    continue
                if challenge.consumed_at is not None or challenge.expires_at <= now:
                    continue
                return code
            return None

    def list_auth_delivery_log(
        self, *, user_id: str | None = None, limit: int = 50
    ) -> tuple[AuthDeliveryLogEntry, ...]:
        rows = list(self.auth_delivery_log.values())
        if user_id is not None:
            rows = [e for e in rows if e.user_id == user_id]
        rows.sort(key=lambda e: e.created_at.isoformat(), reverse=True)
        return tuple(rows[:limit])

    def append_audit(self, event: AuditEvent) -> AuditEvent:
        with self._lock:
            self.audit.append(deepcopy(event))
            return event

    def list_audit(self, *, limit: int = 100) -> tuple[AuditEvent, ...]:
        return tuple(self.audit[-limit:][::-1])
