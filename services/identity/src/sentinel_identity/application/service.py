"""Identity use cases: auth + admin provisioning."""

from __future__ import annotations

import hmac
import uuid
from dataclasses import replace
from datetime import timedelta
from typing import Any

from ..domain.models import (
    AuditEvent,
    AuthChallenge,
    Invitation,
    PrivilegedChangeRequest,
    RoleAssignment,
    SessionRecord,
    User,
)
from ..domain.roles import (
    CONTRACT_VERSION,
    MERCHANT_SUBROLES,
    PRIVILEGED_ROLES,
    assert_staff_role_grantable,
    permissions_for,
)
from .errors import (
    ConflictError,
    ForbiddenError,
    InvalidChallengeError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from .ports import Clock, IdentityStore
from .security import (
    MAX_CHALLENGE_ATTEMPTS,
    assert_password_acceptable,
    hash_password,
    hash_token,
    mint_challenge_code,
    mint_token,
    normalize_email,
    verify_password,
)

SESSION_TTL = timedelta(hours=12)
INVITE_TTL = timedelta(days=7)
CHALLENGE_TTL = timedelta(minutes=15)
NOTIFICATION_LIST_LIMIT = 50
INVALID_CHALLENGE_MESSAGE = "Invalid or expired challenge"
OPS_TEAM_ROLES = frozenset({"operator", "supervisor"})
OPS_TEAM_READERS = frozenset({"supervisor", "platform_admin"})

PRIVILEGED_BODY_FIELDS = frozenset(
    {
        "role",
        "roles",
        "role_id",
        "tenant_id",
        "subject_refs",
        "account_type",
        "authz_version",
        "permissions",
        "granted_by",
    }
)


SANDBOX_PASSWORD_RESET_HINT = (
    "use GET /v1/auth/sandbox/password-reset-code with X-Identity-Sandbox-Token"
)
SANDBOX_LATEST_PURPOSES = frozenset({"email_verify", "mfa"})


class IdentityService:
    def __init__(
        self,
        store: IdentityStore,
        clock: Clock,
        *,
        delivery: Any | None = None,
        expose_sandbox_codes: bool = False,
        sandbox: bool = False,
        sandbox_token: str = "",
    ) -> None:
        self._store = store
        self._clock = clock
        self._delivery = delivery
        self._expose_sandbox_codes = expose_sandbox_codes
        self._sandbox = sandbox
        self._sandbox_token = sandbox_token

    # --- Auth ---

    def register_customer(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        preferred_language: str = "",
        extra: dict[str, Any] | None = None,
        request_id: str = "request-local",
    ) -> dict[str, Any]:
        body = extra or {}
        if PRIVILEGED_BODY_FIELDS & set(body):
            raise ValidationError("Privileged registration fields are not permitted")
        email_n = normalize_email(email)
        if not email_n or not password or not display_name.strip():
            raise ValidationError("email, password and display_name are required")
        try:
            assert_password_acceptable(password)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        if self._store.get_user_by_email(email_n):
            raise ConflictError("Account already exists")
        now = self._clock.now()
        user = User(
            user_id=str(uuid.uuid4()),
            account_type="customer",
            email=email_n,
            display_name=display_name.strip(),
            status="active",
            authz_version=1,
            password_hash=hash_password(password),
            created_at=now,
            updated_at=now,
            tenant_id="tenant-demo",
            preferred_language=preferred_language.strip(),
        )
        self._store.create_user(user)
        assignment = RoleAssignment(
            assignment_id=str(uuid.uuid4()),
            user_id=user.user_id,
            tenant_id="tenant-demo",
            role_id="customer",
            scope_key="tenant:tenant-demo",
            status="active",
            granted_by=None,
            granted_at=now,
        )
        self._store.create_assignment(assignment)
        self._audit(
            actor=user.user_id,
            action="customer.registered",
            target_type="user",
            target_id=user.user_id,
            tenant_id=assignment.tenant_id,
            request_id=request_id,
        )
        token, session = self._issue_session(user, assignment)
        return {
            "user": user.to_public(),
            "assignment": assignment.to_workspace(),
            "session_token": token,
            "expires_at": session.expires_at.isoformat(),
        }

    def login(
        self,
        *,
        email: str,
        password: str,
        requested_role: str | None = None,
        request_id: str = "request-local",
    ) -> dict[str, Any]:
        email_n = normalize_email(email)
        user = self._store.get_user_by_email(email_n)
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid credentials")
        if user.status != "active":
            raise ForbiddenError("Account is not active")
        assignments = [
            a for a in self._store.list_assignments(user.user_id) if a.status == "active"
        ]
        if not assignments:
            raise ForbiddenError("No active workspace")
        selected: RoleAssignment | None = None
        if requested_role:
            matches = [a for a in assignments if a.role_id == requested_role]
            if not matches:
                raise ForbiddenError("Role mismatch for this account")
            selected = matches[0]
        elif len(assignments) == 1:
            selected = assignments[0]
        else:
            raise ConflictError("Multiple workspaces; requested_role required")
        token, session = self._issue_session(user, selected)
        self._audit(
            actor=user.user_id,
            action="session.login",
            target_type="session",
            target_id=session.session_id,
            tenant_id=selected.tenant_id if selected else None,
            request_id=request_id,
        )
        return {
            "user": user.to_public(),
            "workspaces": [a.to_workspace() for a in assignments],
            "active_assignment": selected.to_workspace() if selected else None,
            "session_token": token,
            "expires_at": session.expires_at.isoformat(),
        }

    def logout(self, *, session_token: str, request_id: str = "request-local") -> dict[str, str]:
        session = self._require_session(session_token, allow_stale_authz=True)
        now = self._clock.now()
        self._store.save_session(replace(session, revoked_at=now))
        self._audit(
            actor=session.user_id,
            action="session.logout",
            target_type="session",
            target_id=session.session_id,
            tenant_id=None,
            request_id=request_id,
        )
        return {"status": "revoked"}

    def me(self, *, session_token: str, forged_headers: dict[str, str] | None = None) -> dict:
        ctx = self.resolve_session(session_token)
        if forged_headers:
            role_h = forged_headers.get("x-role") or forged_headers.get("x-sentinel-role")
            tenant_h = forged_headers.get("x-tenant-id") or forged_headers.get("x-sentinel-tenant")
            active = ctx["active_assignment"]
            if role_h and active and role_h != active["role_id"]:
                raise ForbiddenError("Forged role header denied")
            if tenant_h and active and tenant_h != active["tenant_id"]:
                raise ForbiddenError("Forged tenant header denied")
        return ctx

    def update_profile(
        self,
        *,
        session_token: str,
        display_name: str | None = None,
        preferred_language: str | None = None,
        extra: dict[str, Any] | None = None,
        request_id: str = "request-local",
    ) -> dict[str, Any]:
        """Self-service profile patch. Never accepts role/tenant/permission keys."""
        body = extra or {}
        if body:
            raise ValidationError("Unknown or privileged profile fields are not permitted")
        session = self._require_session(session_token)
        user = self._require_user(session.user_id)
        if user.status != "active":
            raise ForbiddenError("Account is not active")
        updates: dict[str, Any] = {"updated_at": self._clock.now()}
        if display_name is not None:
            if not str(display_name).strip():
                raise ValidationError("display_name must not be empty")
            updates["display_name"] = str(display_name).strip()
        if preferred_language is not None:
            updates["preferred_language"] = str(preferred_language).strip()
        user = replace(user, **updates)
        self._store.save_user(user)
        self._audit(
            actor=user.user_id,
            action="profile.updated",
            target_type="user",
            target_id=user.user_id,
            tenant_id=user.tenant_id,
            request_id=request_id,
            details={k: updates[k] for k in ("display_name", "preferred_language") if k in updates},
        )
        return {"user": user.to_public()}

    def list_notifications(self, *, session_token: str) -> dict[str, Any]:
        session = self._require_session(session_token)
        rows = self._store.list_notifications(session.user_id, limit=NOTIFICATION_LIST_LIMIT)
        return {"notifications": [n.to_public() for n in rows]}

    def mark_notification_read(
        self,
        *,
        session_token: str,
        notification_id: str,
        request_id: str = "request-local",
    ) -> dict[str, Any]:
        session = self._require_session(session_token)
        notification = self._store.get_notification(notification_id)
        if notification is None or notification.user_id != session.user_id:
            raise NotFoundError("Notification not found")
        if notification.read_at is None:
            notification = replace(notification, read_at=self._clock.now())
            self._store.save_notification(notification)
            self._audit(
                actor=session.user_id,
                action="notification.read",
                target_type="notification",
                target_id=notification.notification_id,
                tenant_id=None,
                request_id=request_id,
            )
        return {
            "notification_id": notification.notification_id,
            "read_at": notification.read_at.isoformat() if notification.read_at else None,
        }

    def request_email_verify(
        self, *, session_token: str, request_id: str = "request-local"
    ) -> dict[str, Any]:
        session = self._require_session(session_token)
        user = self._require_user(session.user_id)
        raw_code, _challenge = self._issue_challenge(
            user=user,
            challenge_type="email_verify",
            destination=user.email,
            purpose="email_verify",
            request_id=request_id,
        )
        return self._accepted_challenge_response(raw_code)

    def confirm_email_verify(
        self,
        *,
        session_token: str,
        code: str,
        request_id: str = "request-local",
    ) -> dict[str, Any]:
        session = self._require_session(session_token)
        user = self._require_user(session.user_id)
        challenge = self._consume_challenge(
            user_id=user.user_id, challenge_type="email_verify", code=code
        )
        now = self._clock.now()
        user = replace(user, email_verified_at=now, updated_at=now)
        self._store.save_user(user)
        self._audit(
            actor=user.user_id,
            action="email.verified",
            target_type="user",
            target_id=user.user_id,
            tenant_id=user.tenant_id,
            request_id=request_id,
            details={"challenge_id": challenge.challenge_id},
        )
        return {"user": user.to_public(), "email_verified": True}

    def request_mfa_challenge(
        self, *, session_token: str, request_id: str = "request-local"
    ) -> dict[str, Any]:
        """Sandbox MFA: alphanumeric loopback code (not production TOTP)."""
        session = self._require_session(session_token)
        user = self._require_user(session.user_id)
        raw_code, _challenge = self._issue_challenge(
            user=user,
            challenge_type="mfa",
            destination=user.email,
            purpose="mfa",
            request_id=request_id,
        )
        return self._accepted_challenge_response(raw_code)

    def verify_mfa(
        self,
        *,
        session_token: str,
        code: str,
        request_id: str = "request-local",
    ) -> dict[str, Any]:
        session = self._require_session(session_token)
        challenge = self._consume_challenge(
            user_id=session.user_id, challenge_type="mfa", code=code
        )
        now = self._clock.now()
        session = replace(session, mfa_verified_at=now)
        self._store.save_session(session)
        self._audit(
            actor=session.user_id,
            action="mfa.verified",
            target_type="session",
            target_id=session.session_id,
            tenant_id=None,
            request_id=request_id,
            details={"challenge_id": challenge.challenge_id},
        )
        mfa_at = session.mfa_verified_at.isoformat() if session.mfa_verified_at else None
        return {"mfa_verified": True, "mfa_verified_at": mfa_at}

    def forgot_password(self, *, email: str, request_id: str = "request-local") -> dict[str, Any]:
        """Always 202-equivalent body; never reveal whether the email exists."""
        email_n = normalize_email(email)
        user = self._store.get_user_by_email(email_n) if email_n else None
        raw_code: str | None = None
        if user is not None and user.status == "active":
            raw_code, _challenge = self._issue_challenge(
                user=user,
                challenge_type="password_reset",
                destination=user.email,
                purpose="password_reset",
                request_id=request_id,
            )
        body = self._accepted_challenge_response(raw_code)
        if self._sandbox:
            # Identical for known and unknown email — no enumeration.
            body["sandbox_hint"] = SANDBOX_PASSWORD_RESET_HINT
        return body

    def sandbox_latest_code(self, *, session_token: str, purpose: str) -> dict[str, str]:
        """Session inbox for latest open verify/MFA code. Sandbox flag required."""
        if not self._sandbox:
            raise NotFoundError("Not found")
        if purpose not in SANDBOX_LATEST_PURPOSES:
            raise ValidationError("purpose must be email_verify or mfa")
        session = self._require_session(session_token)
        code = self._store.peek_auth_sandbox_code(user_id=session.user_id, purpose=purpose)
        if not code:
            raise NotFoundError("Not found")
        return {"code": code}

    def sandbox_password_reset_code(self, *, email: str, sandbox_token: str) -> dict[str, str]:
        """Token-gated reset inbox. Identical 404 for missing user/challenge/bad token."""
        if not self._sandbox:
            raise NotFoundError("Not found")
        expected = self._sandbox_token or ""
        provided = sandbox_token or ""
        if not expected or not hmac.compare_digest(provided, expected):
            raise NotFoundError("Not found")
        email_n = normalize_email(email)
        user = self._store.get_user_by_email(email_n) if email_n else None
        if user is None:
            raise NotFoundError("Not found")
        code = self._store.peek_auth_sandbox_code(user_id=user.user_id, purpose="password_reset")
        if not code:
            raise NotFoundError("Not found")
        return {"code": code}

    def reset_password(
        self,
        *,
        email: str,
        code: str,
        new_password: str,
        request_id: str = "request-local",
    ) -> dict[str, Any]:
        email_n = normalize_email(email)
        try:
            assert_password_acceptable(new_password)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        user = self._store.get_user_by_email(email_n) if email_n else None
        if user is None:
            raise InvalidChallengeError(INVALID_CHALLENGE_MESSAGE)
        challenge = self._consume_challenge(
            user_id=user.user_id, challenge_type="password_reset", code=code
        )
        now = self._clock.now()
        user = replace(
            user,
            password_hash=hash_password(new_password),
            authz_version=user.authz_version + 1,
            updated_at=now,
        )
        self._store.save_user(user)
        self._store.revoke_sessions_for_user(user.user_id, at=now)
        self._audit(
            actor=user.user_id,
            action="password.reset",
            target_type="user",
            target_id=user.user_id,
            tenant_id=user.tenant_id,
            request_id=request_id,
            details={"challenge_id": challenge.challenge_id},
        )
        return {"status": "reset"}

    def list_workspaces(self, *, session_token: str) -> dict[str, Any]:
        ctx = self.resolve_session(session_token)
        return {"workspaces": ctx["workspaces"], "active_assignment": ctx["active_assignment"]}

    def select_workspace(
        self,
        *,
        session_token: str,
        assignment_id: str,
        request_id: str = "request-local",
    ) -> dict[str, Any]:
        session = self._require_session(session_token)
        user = self._require_user(session.user_id)
        assignment = self._store.get_assignment(assignment_id)
        if (
            assignment is None
            or assignment.user_id != user.user_id
            or assignment.status != "active"
        ):
            raise ForbiddenError("Assignment is not authorized for this session")
        now = self._clock.now()
        self._store.save_session(replace(session, revoked_at=now))
        token, new_session = self._issue_session(user, assignment)
        self._audit(
            actor=user.user_id,
            action="workspace.selected",
            target_type="assignment",
            target_id=assignment.assignment_id,
            tenant_id=assignment.tenant_id,
            request_id=request_id,
        )
        return {
            "active_assignment": assignment.to_workspace(),
            "session_token": token,
            "expires_at": new_session.expires_at.isoformat(),
        }

    def accept_invitation(
        self,
        *,
        token: str,
        email: str,
        password: str,
        display_name: str | None = None,
        request_id: str = "request-local",
    ) -> dict[str, Any]:
        invitation = self._store.get_invitation_by_token_hash(hash_token(token))
        if invitation is None:
            raise ForbiddenError("Invitation denied")
        now = self._clock.now()
        if invitation.status != "pending":
            raise ConflictError("Invitation is no longer pending")
        if invitation.expires_at <= now:
            self._store.save_invitation(replace(invitation, status="expired"))
            raise ForbiddenError("Invitation expired")
        if invitation.review_state == "awaiting_review":
            raise ForbiddenError("Invitation awaiting independent review")
        if invitation.review_state == "rejected":
            raise ForbiddenError("Invitation rejected")
        try:
            assert_staff_role_grantable(invitation.role_id)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        email_n = normalize_email(email)
        if email_n != normalize_email(invitation.work_email):
            raise ForbiddenError("Invitation email mismatch")
        existing = self._store.get_user_by_email(email_n)
        if existing and existing.account_type == "customer":
            raise ForbiddenError("Customer accounts cannot accept staff invitations")
        if existing is None:
            try:
                assert_password_acceptable(password)
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc
            user = User(
                user_id=str(uuid.uuid4()),
                account_type="staff",
                email=email_n,
                display_name=(display_name or invitation.display_name).strip(),
                status="active",
                authz_version=1,
                password_hash=hash_password(password),
                created_at=now,
                updated_at=now,
                tenant_id=invitation.tenant_id,
            )
        else:
            if not verify_password(password, existing.password_hash):
                raise UnauthorizedError("Invalid credentials")
            user = existing
            if user.status != "active":
                raise ForbiddenError("Account is not active")
            user = replace(user, authz_version=user.authz_version + 1, updated_at=now)
        if existing is None:
            # First authz bump is implicit at version 1; still bump after grant.
            user = replace(user, authz_version=2, updated_at=now)
        assignment = RoleAssignment(
            assignment_id=str(uuid.uuid4()),
            user_id=user.user_id,
            tenant_id=invitation.tenant_id,
            role_id=invitation.role_id,
            scope_key=invitation.scope_key,
            status="active",
            granted_by=invitation.invited_by,
            granted_at=now,
            merchant_ref=invitation.merchant_ref,
            team_id=invitation.team_id,
            grant_review_id=invitation.privileged_change_id,
        )
        claimed = self._store.consume_invitation_with_assignment(
            token_hash=hash_token(token),
            user=user,
            assignment=assignment,
            at=now,
        )
        self._audit(
            actor=user.user_id,
            action="invitation.accepted",
            target_type="invitation",
            target_id=claimed.invitation_id,
            tenant_id=invitation.tenant_id,
            request_id=request_id,
            details={"role_id": invitation.role_id},
        )
        session_token, session = self._issue_session(user, assignment)
        return {
            "user": user.to_public(),
            "assignment": assignment.to_workspace(),
            "session_token": session_token,
            "expires_at": session.expires_at.isoformat(),
            "invitation_id": claimed.invitation_id,
        }

    def resolve_session(self, session_token: str) -> dict[str, Any]:
        session = self._require_session(session_token)
        user = self._require_user(session.user_id)
        if user.status != "active":
            raise ForbiddenError("Account is not active")
        assignments = [
            a for a in self._store.list_assignments(user.user_id) if a.status == "active"
        ]
        active = None
        if session.assignment_id:
            for a in assignments:
                if a.assignment_id == session.assignment_id:
                    active = a
                    break
            if active is None:
                raise ForbiddenError("Active assignment revoked")
        perms: list[str] = []
        if active:
            perms = sorted(permissions_for(active.role_id))
        return {
            "user": user.to_public(),
            "workspaces": [a.to_workspace() for a in assignments],
            "active_assignment": active.to_workspace() if active else None,
            "permissions": perms,
        }

    def list_merchant_memberships(
        self,
        *,
        session_token: str,
        tenant_id: str,
        merchant_ref: str,
    ) -> dict[str, Any]:
        """Project merchant-scoped role assignments for merchant-teams.v1 peers."""
        if not tenant_id.strip() or not merchant_ref.strip():
            raise ValidationError("tenant_id and merchant_ref are required")
        self._require_membership_reader(
            session_token, tenant_id=tenant_id, merchant_ref=merchant_ref
        )
        rows = self._store.list_assignments_for_merchant(
            tenant_id=tenant_id, merchant_ref=merchant_ref
        )
        memberships: list[dict[str, Any]] = []
        for assignment in rows:
            if assignment.status != "active":
                continue
            subroles = _subroles_for_merchant_assignment(assignment)
            if not subroles:
                continue
            user = self._store.get_user(assignment.user_id)
            if user is None or user.status != "active":
                continue
            memberships.append(
                {
                    "membership_id": assignment.assignment_id,
                    "assignment_id": assignment.assignment_id,
                    "user_id": assignment.user_id,
                    "tenant_id": assignment.tenant_id,
                    "merchant_ref": assignment.merchant_ref,
                    "display_name": user.display_name,
                    "subroles": subroles,
                    "status": assignment.status,
                }
            )
        return {"contract_version": CONTRACT_VERSION, "memberships": memberships}

    def list_ops_team(self, *, session_token: str) -> dict[str, Any]:
        """Tenant-scoped operator/supervisor roster for supervisor portal (not full admin)."""
        ctx = self._require_ops_team_reader(session_token)
        active = ctx["active_assignment"]
        tenant_id = active["tenant_id"]
        members: list[dict[str, Any]] = []
        for user in self._store.list_users():
            if user.account_type != "staff" or user.status != "active":
                continue
            for assignment in self._store.list_assignments(user.user_id):
                if assignment.status != "active":
                    continue
                if assignment.tenant_id != tenant_id:
                    continue
                if assignment.role_id not in OPS_TEAM_ROLES:
                    continue
                members.append(
                    {
                        "user_id": user.user_id,
                        "email": user.email,
                        "display_name": user.display_name,
                        "role": assignment.role_id,
                        "assignment_id": assignment.assignment_id,
                    }
                )
        members.sort(key=lambda row: (row["role"], row["email"]))
        return {
            "contract_version": CONTRACT_VERSION,
            "tenant_id": tenant_id,
            "members": members,
        }

    # --- Admin ---

    def admin_invite(
        self,
        *,
        session_token: str,
        display_name: str,
        work_email: str,
        tenant_id: str,
        role_id: str,
        reason: str | None = None,
        idempotency_key: str | None = None,
        scope: dict[str, Any] | None = None,
        request_id: str = "request-local",
    ) -> dict[str, Any]:
        admin = self._require_admin(session_token)
        try:
            assert_staff_role_grantable(role_id)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        email_n = normalize_email(work_email)
        if not display_name.strip() or not email_n or not tenant_id.strip():
            raise ValidationError("display_name, work_email and tenant_id are required")
        key = idempotency_key or str(uuid.uuid4())
        existing = self._store.get_invitation_by_idempotency(key)
        if existing is not None:
            return {
                "invitation": existing.to_public(),
                "delivery_hint": "idempotent_replay",
                "idempotent_replay": True,
            }
        existing_user = self._store.get_user_by_email(email_n)
        if existing_user is not None and existing_user.status == "active":
            raise ConflictError("Account already exists")
        scope = scope or {}
        team_id = scope.get("team_id")
        merchant_ref = scope.get("merchant_ref")
        scope_key = f"tenant:{tenant_id}"
        if merchant_ref:
            scope_key = f"{scope_key}|merchant:{merchant_ref}"
        if team_id:
            scope_key = f"{scope_key}|team:{team_id}"
        now = self._clock.now()
        raw_token = mint_token()
        privileged = role_id in PRIVILEGED_ROLES
        change_id = str(uuid.uuid4()) if privileged else None
        invitation = Invitation(
            invitation_id=str(uuid.uuid4()),
            work_email=email_n,
            display_name=display_name.strip(),
            tenant_id=tenant_id,
            role_id=role_id,
            scope_key=scope_key,
            token_hash=hash_token(raw_token),
            status="pending",
            invited_by=admin["user"]["user_id"],
            created_at=now,
            expires_at=now + INVITE_TTL,
            idempotency_key=key,
            review_state="awaiting_review" if privileged else "not_required",
            privileged_change_id=change_id,
            merchant_ref=merchant_ref,
            team_id=team_id,
            reason=reason,
        )
        self._store.create_invitation(invitation)
        self._store.record_delivery_secret(
            invitation.invitation_id,
            raw_token,
            work_email=invitation.work_email,
        )
        self.flush_delivery_outbox()
        if privileged and change_id is not None:
            self._store.create_privileged_change(
                PrivilegedChangeRequest(
                    change_id=change_id,
                    kind="invite",
                    state="pending",
                    maker_user_id=admin["user"]["user_id"],
                    role_id=role_id,
                    tenant_id=tenant_id,
                    created_at=now,
                    invitation_id=invitation.invitation_id,
                    reason=reason,
                )
            )
        self._audit(
            actor=admin["user"]["user_id"],
            action="invitation.created",
            target_type="invitation",
            target_id=invitation.invitation_id,
            tenant_id=tenant_id,
            request_id=request_id,
            details={"role_id": role_id, "privileged": privileged},
        )
        return {
            "invitation": invitation.to_public(),
            "delivery_hint": "queued_for_delivery_adapter",
            "privileged_change_id": change_id,
        }

    def flush_delivery_outbox(self) -> dict[str, Any]:
        """Drain durable invite delivery outbox into the sandbox inbox."""
        if self._delivery is None:
            return {"delivered": 0, "adapter": "none"}
        delivered = int(self._delivery.drain())
        return {"delivered": delivered, "adapter": "sandbox_inbox"}

    def list_sandbox_inbox(self, *, work_email: str | None = None) -> dict[str, Any]:
        """Local demo inbox: acceptance links from delivered outbox rows."""
        if self._delivery is not None and hasattr(self._delivery, "drain"):
            self._delivery.drain()
        rows = self._store.list_sandbox_inbox(work_email=work_email)
        return {
            "evidence_label": "sandbox_inbox",
            "messages": [row.to_inbox() for row in rows],
        }

    def admin_list_invitations(self, *, session_token: str) -> dict[str, Any]:
        self._require_admin(session_token)
        rows = self._store.list_invitations()
        return {"invitations": [i.to_public() for i in rows]}

    def admin_revoke_invitation(
        self, *, session_token: str, invitation_id: str, request_id: str = "request-local"
    ) -> dict[str, Any]:
        admin = self._require_admin(session_token)
        invitation = self._store.get_invitation(invitation_id)
        if invitation is None:
            raise NotFoundError("Invitation not found")
        if invitation.status != "pending":
            raise ConflictError("Invitation is not pending")
        now = self._clock.now()
        invitation = replace(invitation, status="revoked", revoked_at=now)
        self._store.save_invitation(invitation)
        self._audit(
            actor=admin["user"]["user_id"],
            action="invitation.revoked",
            target_type="invitation",
            target_id=invitation_id,
            tenant_id=invitation.tenant_id,
            request_id=request_id,
        )
        return {"invitation": invitation.to_public()}

    def admin_list_users(self, *, session_token: str) -> dict[str, Any]:
        self._require_admin(session_token)
        users = self._store.list_users()
        out = []
        for u in users:
            if u.account_type != "staff":
                continue
            assignments = [
                a.to_workspace()
                for a in self._store.list_assignments(u.user_id)
                if a.status == "active"
            ]
            out.append({**u.to_public(), "assignments": assignments})
        return {"users": out}

    def admin_grant_role(
        self,
        *,
        session_token: str,
        user_id: str,
        tenant_id: str,
        role_id: str,
        merchant_ref: str | None = None,
        team_id: str | None = None,
        request_id: str = "request-local",
    ) -> dict[str, Any]:
        admin = self._require_admin(session_token)
        admin_id = admin["user"]["user_id"]
        try:
            assert_staff_role_grantable(role_id)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        user = self._require_user(user_id)
        if user.account_type != "staff":
            raise ValidationError("Only staff accounts receive staff role grants")
        privileged = role_id in PRIVILEGED_ROLES
        if privileged and user_id == admin_id:
            raise ForbiddenError("Privileged self-grant requires independent review")
        now = self._clock.now()
        scope_key = f"tenant:{tenant_id}"
        if merchant_ref:
            scope_key = f"{scope_key}|merchant:{merchant_ref}"
        if team_id:
            scope_key = f"{scope_key}|team:{team_id}"
        change_id = str(uuid.uuid4()) if privileged else None
        assignment = RoleAssignment(
            assignment_id=str(uuid.uuid4()),
            user_id=user.user_id,
            tenant_id=tenant_id,
            role_id=role_id,
            scope_key=scope_key,
            status="pending" if privileged else "active",
            granted_by=admin_id,
            granted_at=now,
            merchant_ref=merchant_ref,
            team_id=team_id,
            grant_review_id=change_id,
        )
        change: PrivilegedChangeRequest | None = None
        if privileged and change_id is not None:
            change = PrivilegedChangeRequest(
                change_id=change_id,
                kind="grant",
                state="pending",
                maker_user_id=admin_id,
                role_id=role_id,
                tenant_id=tenant_id,
                created_at=now,
                target_user_id=user_id,
                assignment_id=assignment.assignment_id,
            )
            # Pending privileged grant: store assignment + change; no authz bump yet.
            self._store.create_assignment(assignment)
            self._store.create_privileged_change(change)
            self._audit(
                actor=admin_id,
                action="role.grant_pending_review",
                target_type="assignment",
                target_id=assignment.assignment_id,
                tenant_id=tenant_id,
                request_id=request_id,
                details={"role_id": role_id, "user_id": user_id, "change_id": change_id},
            )
            return {
                "assignment": assignment.to_workspace(),
                "user": user.to_public(),
                "privileged_change": change.to_public(),
                "effective": False,
            }

        bumped = replace(user, authz_version=user.authz_version + 1, updated_at=now)
        self._store.apply_authz_bundle(
            user=bumped,
            assignment=assignment,
            assignment_mode="create",
            at=now,
            revoke_sessions=True,
        )
        self._audit(
            actor=admin_id,
            action="role.granted",
            target_type="assignment",
            target_id=assignment.assignment_id,
            tenant_id=tenant_id,
            request_id=request_id,
            details={"role_id": role_id, "user_id": user_id},
        )
        return {
            "assignment": assignment.to_workspace(),
            "user": bumped.to_public(),
            "effective": True,
        }

    def admin_decide_privileged_change(
        self,
        *,
        session_token: str,
        change_id: str,
        decision: str,
        reason: str | None = None,
        request_id: str = "request-local",
    ) -> dict[str, Any]:
        admin = self._require_admin(session_token)
        reviewer_id = admin["user"]["user_id"]
        change = self._store.get_privileged_change(change_id)
        if change is None:
            raise NotFoundError("Privileged change not found")
        if change.state != "pending":
            raise ConflictError("Privileged change is not pending")
        if change.maker_user_id == reviewer_id:
            raise ForbiddenError("Independent reviewer required")
        if decision not in {"approve", "reject"}:
            raise ValidationError("decision must be approve or reject")
        now = self._clock.now()
        if decision == "reject":
            rejected = replace(
                change,
                state="rejected",
                reviewer_user_id=reviewer_id,
                decided_at=now,
                decision_reason=reason,
            )
            invitation = None
            assignment = None
            user = None
            if change.invitation_id:
                inv = self._store.get_invitation(change.invitation_id)
                if inv is not None and inv.status == "pending":
                    invitation = replace(inv, review_state="rejected")
            if change.assignment_id:
                assignment = self._store.get_assignment(change.assignment_id)
                if assignment is not None and assignment.status == "pending":
                    assignment = replace(assignment, status="revoked", revoked_at=now)
                    user = self._require_user(assignment.user_id)
            if assignment is not None and user is not None:
                self._store.apply_authz_bundle(
                    user=user,
                    assignment=assignment,
                    assignment_mode="save",
                    at=now,
                    revoke_sessions=False,
                    change=rejected,
                    invitation=invitation,
                )
            else:
                self._store.save_privileged_change(rejected)
                if invitation is not None:
                    self._store.save_invitation(invitation)
            self._audit(
                actor=reviewer_id,
                action="privileged_change.rejected",
                target_type="privileged_change",
                target_id=change_id,
                tenant_id=change.tenant_id,
                request_id=request_id,
            )
            return {"privileged_change": rejected.to_public(), "effective": False}

        approved = replace(
            change,
            state="approved",
            reviewer_user_id=reviewer_id,
            decided_at=now,
            decision_reason=reason,
        )
        if change.kind == "invite":
            inv = self._store.get_invitation(change.invitation_id or "")
            if inv is None:
                raise NotFoundError("Invitation not found")
            invitation = replace(inv, review_state="approved")
            self._store.save_privileged_change(approved)
            self._store.save_invitation(invitation)
            self._audit(
                actor=reviewer_id,
                action="privileged_change.approved",
                target_type="privileged_change",
                target_id=change_id,
                tenant_id=change.tenant_id,
                request_id=request_id,
            )
            return {
                "privileged_change": approved.to_public(),
                "invitation": invitation.to_public(),
                "effective": False,
                "note": "Invitation approved; accept still required",
            }

        # grant activation
        assignment = self._store.get_assignment(change.assignment_id or "")
        if assignment is None:
            raise NotFoundError("Assignment not found")
        if assignment.status != "pending":
            raise ConflictError("Assignment is not pending")
        user = self._require_user(assignment.user_id)
        active = replace(assignment, status="active")
        bumped = replace(user, authz_version=user.authz_version + 1, updated_at=now)
        self._store.apply_authz_bundle(
            user=bumped,
            assignment=active,
            assignment_mode="save",
            at=now,
            revoke_sessions=True,
            change=approved,
        )
        self._audit(
            actor=reviewer_id,
            action="privileged_change.approved",
            target_type="privileged_change",
            target_id=change_id,
            tenant_id=change.tenant_id,
            request_id=request_id,
        )
        return {
            "privileged_change": approved.to_public(),
            "assignment": active.to_workspace(),
            "user": bumped.to_public(),
            "effective": True,
        }

    def admin_revoke_role(
        self,
        *,
        session_token: str,
        user_id: str,
        assignment_id: str,
        request_id: str = "request-local",
    ) -> dict[str, Any]:
        admin = self._require_admin(session_token)
        user = self._require_user(user_id)
        assignment = self._store.get_assignment(assignment_id)
        if assignment is None or assignment.user_id != user_id:
            raise NotFoundError("Assignment not found")
        if assignment.status not in {"active", "pending"}:
            raise ConflictError("Assignment is not active")
        now = self._clock.now()
        assignment = replace(assignment, status="revoked", revoked_at=now)
        bumped = replace(user, authz_version=user.authz_version + 1, updated_at=now)
        self._store.apply_authz_bundle(
            user=bumped,
            assignment=assignment,
            assignment_mode="save",
            at=now,
            revoke_sessions=True,
        )
        self._audit(
            actor=admin["user"]["user_id"],
            action="role.revoked",
            target_type="assignment",
            target_id=assignment_id,
            tenant_id=assignment.tenant_id,
            request_id=request_id,
        )
        return {"assignment": assignment.to_workspace(), "user": bumped.to_public()}

    def admin_suspend(
        self, *, session_token: str, user_id: str, request_id: str = "request-local"
    ) -> dict[str, Any]:
        admin = self._require_admin(session_token)
        user = self._require_user(user_id)
        now = self._clock.now()
        user = replace(
            user,
            status="suspended",
            authz_version=user.authz_version + 1,
            updated_at=now,
        )
        self._store.save_user(user)
        self._store.revoke_sessions_for_user(user.user_id, at=now)
        self._audit(
            actor=admin["user"]["user_id"],
            action="user.suspended",
            target_type="user",
            target_id=user_id,
            tenant_id=user.tenant_id,
            request_id=request_id,
        )
        return {"user": user.to_public()}

    def admin_reactivate(
        self, *, session_token: str, user_id: str, request_id: str = "request-local"
    ) -> dict[str, Any]:
        admin = self._require_admin(session_token)
        user = self._require_user(user_id)
        if user.status not in {"suspended", "deactivated"}:
            raise ConflictError("User is not suspended or deactivated")
        now = self._clock.now()
        user = replace(
            user,
            status="active",
            authz_version=user.authz_version + 1,
            updated_at=now,
        )
        self._store.save_user(user)
        self._audit(
            actor=admin["user"]["user_id"],
            action="user.reactivated",
            target_type="user",
            target_id=user_id,
            tenant_id=user.tenant_id,
            request_id=request_id,
        )
        return {"user": user.to_public()}

    def admin_list_roles(self, *, session_token: str) -> dict[str, Any]:
        self._require_admin(session_token)
        from ..domain.roles import HUMAN_ROLES, SERVICE_ROLES, STAFF_INVITABLE_ROLES

        return {
            "human_roles": sorted(HUMAN_ROLES),
            "staff_invitable_roles": sorted(STAFF_INVITABLE_ROLES),
            "service_roles": sorted(SERVICE_ROLES),
        }

    def admin_list_audit(self, *, session_token: str, limit: int = 100) -> dict[str, Any]:
        self._require_admin(session_token)
        return {"events": [e.to_public() for e in self._store.list_audit(limit=limit)]}

    def admin_revoke_sessions(
        self, *, session_token: str, user_id: str, request_id: str = "request-local"
    ) -> dict[str, Any]:
        admin = self._require_admin(session_token)
        self._require_user(user_id)
        now = self._clock.now()
        count = self._store.revoke_sessions_for_user(user_id, at=now)
        self._audit(
            actor=admin["user"]["user_id"],
            action="sessions.revoked",
            target_type="user",
            target_id=user_id,
            tenant_id=None,
            request_id=request_id,
            details={"count": count},
        )
        return {"revoked": count}

    # --- Internals ---

    def _require_admin(self, session_token: str) -> dict[str, Any]:
        ctx = self.resolve_session(session_token)
        active = ctx.get("active_assignment")
        if not active or active["role_id"] != "platform_admin":
            raise ForbiddenError("Platform Admin assignment required")
        return ctx

    def _require_ops_team_reader(self, session_token: str) -> dict[str, Any]:
        ctx = self.resolve_session(session_token)
        active = ctx.get("active_assignment")
        if not active or active["role_id"] not in OPS_TEAM_READERS:
            raise ForbiddenError("Supervisor or Platform Admin assignment required")
        if not active.get("tenant_id"):
            raise ForbiddenError("Active assignment tenant required")
        return ctx

    def _require_membership_reader(
        self, session_token: str, *, tenant_id: str, merchant_ref: str
    ) -> dict[str, Any]:
        ctx = self.resolve_session(session_token)
        active = ctx.get("active_assignment")
        if not active:
            raise ForbiddenError("Active assignment required")
        if active["role_id"] == "platform_admin":
            return ctx
        if (
            active["tenant_id"] == tenant_id
            and active.get("merchant_ref") == merchant_ref
            and active["role_id"] == "merchant"
        ):
            return ctx
        raise ForbiddenError("Merchant membership read not authorized")

    def _require_user(self, user_id: str) -> User:
        user = self._store.get_user(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    def _require_session(
        self, session_token: str, *, allow_stale_authz: bool = False
    ) -> SessionRecord:
        if not session_token:
            raise UnauthorizedError("Missing session")
        session = self._store.get_session_by_token_hash(hash_token(session_token))
        if session is None:
            raise UnauthorizedError("Invalid session")
        now = self._clock.now()
        if session.revoked_at is not None:
            raise UnauthorizedError("Session revoked")
        if session.expires_at <= now:
            raise UnauthorizedError("Session expired")
        user = self._store.get_user(session.user_id)
        if user is None:
            raise UnauthorizedError("Invalid session")
        if not allow_stale_authz and session.authz_version != user.authz_version:
            raise ForbiddenError("Authorization version mismatch")
        if user.status == "suspended":
            raise ForbiddenError("Account suspended")
        return session

    def _issue_session(
        self, user: User, assignment: RoleAssignment | None
    ) -> tuple[str, SessionRecord]:
        now = self._clock.now()
        raw = mint_token()
        session = SessionRecord(
            session_id=str(uuid.uuid4()),
            token_hash=hash_token(raw),
            user_id=user.user_id,
            assignment_id=assignment.assignment_id if assignment else None,
            authz_version=user.authz_version,
            issued_at=now,
            expires_at=now + SESSION_TTL,
        )
        self._store.create_session(session)
        return raw, session

    def _issue_challenge(
        self,
        *,
        user: User,
        challenge_type: str,
        destination: str,
        purpose: str,
        request_id: str,
    ) -> tuple[str, AuthChallenge]:
        now = self._clock.now()
        raw_code = mint_challenge_code()
        challenge = AuthChallenge(
            challenge_id=str(uuid.uuid4()),
            user_id=user.user_id,
            challenge_type=challenge_type,
            code_hash=hash_token(raw_code),
            expires_at=now + CHALLENGE_TTL,
            created_at=now,
            attempt_count=0,
        )
        self._store.create_auth_challenge(challenge)
        self._store.append_auth_delivery(
            challenge_id=challenge.challenge_id,
            user_id=user.user_id,
            destination=destination,
            purpose=purpose,
            at=now,
            # Persist plaintext only for sandbox product-demo inbox.
            raw_code=raw_code if self._sandbox else "",
        )
        self._audit(
            actor=user.user_id,
            action=f"challenge.{purpose}.issued",
            target_type="auth_challenge",
            target_id=challenge.challenge_id,
            tenant_id=user.tenant_id,
            request_id=request_id,
            details={"channel": "loopback", "destination": destination},
        )
        return raw_code, challenge

    def _consume_challenge(self, *, user_id: str, challenge_type: str, code: str) -> AuthChallenge:
        now = self._clock.now()
        challenge = self._store.get_active_auth_challenge(
            user_id=user_id, challenge_type=challenge_type, at=now
        )
        if challenge is None or not code:
            raise InvalidChallengeError(INVALID_CHALLENGE_MESSAGE)
        if hmac.compare_digest(hash_token(code), challenge.code_hash):
            consumed = self._store.try_consume_auth_challenge(challenge.challenge_id, at=now)
            if consumed is None:
                raise InvalidChallengeError(INVALID_CHALLENGE_MESSAGE)
            return consumed
        self._store.record_auth_challenge_failure(
            challenge.challenge_id, at=now, max_attempts=MAX_CHALLENGE_ATTEMPTS
        )
        raise InvalidChallengeError(INVALID_CHALLENGE_MESSAGE)

    def _accepted_challenge_response(self, raw_code: str | None) -> dict[str, Any]:
        body: dict[str, Any] = {"status": "accepted"}
        if self._expose_sandbox_codes and raw_code:
            body["sandbox_code"] = raw_code
        return body

    def _audit(
        self,
        *,
        actor: str | None,
        action: str,
        target_type: str,
        target_id: str,
        tenant_id: str | None,
        request_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            actor_user_id=actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            tenant_id=tenant_id,
            at=self._clock.now(),
            details=details or {},
            request_id=request_id,
        )
        self._store.append_audit(event)


def _subroles_for_merchant_assignment(assignment: RoleAssignment) -> list[str]:
    """Map identity role grant → merchant-teams subroles (never platform roles)."""
    if assignment.role_id in MERCHANT_SUBROLES:
        return [assignment.role_id]
    if assignment.role_id == "merchant":
        return ["admin"]
    return []
