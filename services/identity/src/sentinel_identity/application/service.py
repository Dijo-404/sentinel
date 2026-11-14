"""Identity use cases: auth + admin provisioning."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import timedelta
from typing import Any

from ..domain.models import (
    AuditEvent,
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
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from .ports import Clock, IdentityStore
from .security import (
    assert_password_acceptable,
    hash_password,
    hash_token,
    mint_token,
    normalize_email,
    verify_password,
)

SESSION_TTL = timedelta(hours=12)
INVITE_TTL = timedelta(days=7)

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


class IdentityService:
    def __init__(
        self,
        store: IdentityStore,
        clock: Clock,
        *,
        delivery: Any | None = None,
    ) -> None:
        self._store = store
        self._clock = clock
        self._delivery = delivery

    # --- Auth ---

    def register_customer(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
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
