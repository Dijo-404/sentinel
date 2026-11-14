"""PostgreSQL identity store (identity-owned schema only)."""

from __future__ import annotations

import json
import uuid
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, text

from ..application.errors import ConflictError, ForbiddenError
from ..domain.models import (
    AuditEvent,
    DeliveryOutboxItem,
    Invitation,
    PrivilegedChangeRequest,
    RoleAssignment,
    SessionRecord,
    User,
)

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"


def make_engine(database_url: str) -> Engine:
    return create_engine(database_url, hide_parameters=True, future=True)


def ensure_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            ddl = path.read_text(encoding="utf-8")
            for stmt in _split_sql(ddl):
                conn.execute(text(stmt))


def _split_sql(ddl: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    for line in ddl.splitlines():
        if line.strip().startswith("--"):
            continue
        buf.append(line)
        if line.rstrip().endswith(";"):
            stmt = "\n".join(buf).strip().rstrip(";").strip()
            if stmt:
                parts.append(stmt)
            buf = []
    tail = "\n".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def _dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    raise TypeError(f"expected datetime, got {type(value)!r}")


class PostgresIdentityStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create_user(self, user: User) -> User:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO identity.users (
                        user_id, account_type, email, display_name, status,
                        authz_version, password_hash, tenant_id, created_at, updated_at,
                        preferred_language
                    ) VALUES (
                        :user_id, :account_type, :email, :display_name, :status,
                        :authz_version, :password_hash, :tenant_id, :created_at, :updated_at,
                        :preferred_language
                    )
                    """
                ),
                user.__dict__,
            )
        return user

    def get_user(self, user_id: str) -> User | None:
        with self._engine.connect() as conn:
            row = (
                conn.execute(
                    text("SELECT * FROM identity.users WHERE user_id = :user_id"),
                    {"user_id": user_id},
                )
                .mappings()
                .first()
            )
        return _user_from_row(row) if row else None

    def get_user_by_email(self, email: str) -> User | None:
        with self._engine.connect() as conn:
            row = (
                conn.execute(
                    text("SELECT * FROM identity.users WHERE email = :email"),
                    {"email": email},
                )
                .mappings()
                .first()
            )
        return _user_from_row(row) if row else None

    def save_user(self, user: User) -> User:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE identity.users SET
                        account_type=:account_type, email=:email,
                        display_name=:display_name, status=:status,
                        authz_version=:authz_version, password_hash=:password_hash,
                        tenant_id=:tenant_id, updated_at=:updated_at,
                        preferred_language=:preferred_language
                    WHERE user_id=:user_id
                    """
                ),
                user.__dict__,
            )
        return user

    def list_users(self, *, tenant_id: str | None = None) -> tuple[User, ...]:
        sql = "SELECT * FROM identity.users"
        params: dict[str, Any] = {}
        if tenant_id is not None:
            sql += " WHERE tenant_id = :tenant_id"
            params["tenant_id"] = tenant_id
        sql += " ORDER BY email"
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return tuple(_user_from_row(r) for r in rows)

    def create_assignment(self, assignment: RoleAssignment) -> RoleAssignment:
        with self._engine.begin() as conn:
            _insert_assignment(conn, assignment)
        return assignment

    def get_assignment(self, assignment_id: str) -> RoleAssignment | None:
        with self._engine.connect() as conn:
            row = (
                conn.execute(
                    text("SELECT * FROM identity.role_assignments WHERE assignment_id = :id"),
                    {"id": assignment_id},
                )
                .mappings()
                .first()
            )
        return _assignment_from_row(row) if row else None

    def save_assignment(self, assignment: RoleAssignment) -> RoleAssignment:
        with self._engine.begin() as conn:
            _update_assignment(conn, assignment)
        return assignment

    def list_assignments(self, user_id: str) -> tuple[RoleAssignment, ...]:
        with self._engine.connect() as conn:
            rows = (
                conn.execute(
                    text(
                        """
                        SELECT * FROM identity.role_assignments
                        WHERE user_id = :user_id ORDER BY granted_at
                        """
                    ),
                    {"user_id": user_id},
                )
                .mappings()
                .all()
            )
        return tuple(_assignment_from_row(r) for r in rows)

    def list_assignments_for_merchant(
        self, *, tenant_id: str, merchant_ref: str
    ) -> tuple[RoleAssignment, ...]:
        with self._engine.connect() as conn:
            rows = (
                conn.execute(
                    text(
                        """
                        SELECT * FROM identity.role_assignments
                        WHERE tenant_id = :tenant_id AND merchant_ref = :merchant_ref
                        ORDER BY granted_at
                        """
                    ),
                    {"tenant_id": tenant_id, "merchant_ref": merchant_ref},
                )
                .mappings()
                .all()
            )
        return tuple(_assignment_from_row(r) for r in rows)

    def create_session(self, session: SessionRecord) -> SessionRecord:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO identity.sessions (
                        session_id, token_hash, user_id, assignment_id, authz_version,
                        mfa_verified_at, issued_at, expires_at, revoked_at
                    ) VALUES (
                        :session_id, :token_hash, :user_id, :assignment_id, :authz_version,
                        :mfa_verified_at, :issued_at, :expires_at, :revoked_at
                    )
                    """
                ),
                session.__dict__,
            )
        return session

    def get_session_by_token_hash(self, token_hash: str) -> SessionRecord | None:
        with self._engine.connect() as conn:
            row = (
                conn.execute(
                    text("SELECT * FROM identity.sessions WHERE token_hash = :token_hash"),
                    {"token_hash": token_hash},
                )
                .mappings()
                .first()
            )
        return _session_from_row(row) if row else None

    def save_session(self, session: SessionRecord) -> SessionRecord:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE identity.sessions SET
                        assignment_id=:assignment_id, authz_version=:authz_version,
                        revoked_at=:revoked_at, mfa_verified_at=:mfa_verified_at
                    WHERE session_id=:session_id
                    """
                ),
                session.__dict__,
            )
        return session

    def revoke_sessions_for_user(self, user_id: str, *, at: datetime) -> int:
        with self._engine.begin() as conn:
            return _revoke_sessions(conn, user_id, at)

    def create_invitation(self, invitation: Invitation) -> Invitation:
        with self._engine.begin() as conn:
            _insert_invitation(conn, invitation)
        return invitation

    def get_invitation(self, invitation_id: str) -> Invitation | None:
        with self._engine.connect() as conn:
            row = (
                conn.execute(
                    text("SELECT * FROM identity.staff_invitations WHERE invitation_id = :id"),
                    {"id": invitation_id},
                )
                .mappings()
                .first()
            )
        return _invitation_from_row(row) if row else None

    def get_invitation_by_idempotency(self, key: str) -> Invitation | None:
        with self._engine.connect() as conn:
            row = (
                conn.execute(
                    text("SELECT * FROM identity.staff_invitations WHERE idempotency_key = :key"),
                    {"key": key},
                )
                .mappings()
                .first()
            )
        return _invitation_from_row(row) if row else None

    def get_invitation_by_token_hash(self, token_hash: str) -> Invitation | None:
        with self._engine.connect() as conn:
            row = (
                conn.execute(
                    text("SELECT * FROM identity.staff_invitations WHERE token_hash = :token_hash"),
                    {"token_hash": token_hash},
                )
                .mappings()
                .first()
            )
        return _invitation_from_row(row) if row else None

    def save_invitation(self, invitation: Invitation) -> Invitation:
        with self._engine.begin() as conn:
            _update_invitation(conn, invitation)
        return invitation

    def list_invitations(self, *, tenant_id: str | None = None) -> tuple[Invitation, ...]:
        sql = "SELECT * FROM identity.staff_invitations"
        params: dict[str, Any] = {}
        if tenant_id is not None:
            sql += " WHERE tenant_id = :tenant_id"
            params["tenant_id"] = tenant_id
        sql += " ORDER BY created_at DESC"
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return tuple(_invitation_from_row(r) for r in rows)

    def consume_invitation_with_assignment(
        self,
        *,
        token_hash: str,
        user: User,
        assignment: RoleAssignment,
        at: datetime,
    ) -> Invitation:
        with self._engine.begin() as conn:
            row = (
                conn.execute(
                    text(
                        """
                        SELECT * FROM identity.staff_invitations
                        WHERE token_hash = :token_hash FOR UPDATE
                        """
                    ),
                    {"token_hash": token_hash},
                )
                .mappings()
                .first()
            )
            if row is None:
                raise ForbiddenError("Invitation denied")
            invitation = _invitation_from_row(row)
            if invitation.status != "pending":
                raise ConflictError("Invitation is no longer pending")
            if invitation.review_state == "awaiting_review":
                raise ForbiddenError("Invitation awaiting independent review")
            if invitation.review_state == "rejected":
                raise ForbiddenError("Invitation rejected")
            if invitation.expires_at <= at:
                conn.execute(
                    text(
                        """
                        UPDATE identity.staff_invitations
                        SET status = 'expired' WHERE invitation_id = :id
                        """
                    ),
                    {"id": invitation.invitation_id},
                )
                raise ForbiddenError("Invitation expired")
            existing = (
                conn.execute(
                    text("SELECT user_id FROM identity.users WHERE user_id = :user_id"),
                    {"user_id": user.user_id},
                )
                .mappings()
                .first()
            )
            if existing is None:
                conn.execute(
                    text(
                        """
                        INSERT INTO identity.users (
                            user_id, account_type, email, display_name, status,
                            authz_version, password_hash, tenant_id, created_at, updated_at,
                            preferred_language
                        ) VALUES (
                            :user_id, :account_type, :email, :display_name, :status,
                            :authz_version, :password_hash, :tenant_id, :created_at, :updated_at,
                            :preferred_language
                        )
                        """
                    ),
                    user.__dict__,
                )
            else:
                conn.execute(
                    text(
                        """
                        UPDATE identity.users SET
                            authz_version=:authz_version, updated_at=:updated_at,
                            password_hash=:password_hash, display_name=:display_name,
                            status=:status, preferred_language=:preferred_language
                        WHERE user_id=:user_id
                        """
                    ),
                    user.__dict__,
                )
            claimed = replace(
                invitation,
                status="accepted",
                accepted_at=at,
                accepted_user_id=user.user_id,
            )
            _update_invitation(conn, claimed)
            _insert_assignment(conn, assignment)
            return claimed

    def create_privileged_change(self, change: PrivilegedChangeRequest) -> PrivilegedChangeRequest:
        with self._engine.begin() as conn:
            _insert_change(conn, change)
        return change

    def get_privileged_change(self, change_id: str) -> PrivilegedChangeRequest | None:
        with self._engine.connect() as conn:
            row = (
                conn.execute(
                    text(
                        """
                        SELECT * FROM identity.privileged_change_requests
                        WHERE change_id = :id
                        """
                    ),
                    {"id": change_id},
                )
                .mappings()
                .first()
            )
        return _change_from_row(row) if row else None

    def save_privileged_change(self, change: PrivilegedChangeRequest) -> PrivilegedChangeRequest:
        with self._engine.begin() as conn:
            _update_change(conn, change)
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
        with self._engine.begin() as conn:
            if assignment_mode == "create":
                _insert_assignment(conn, assignment)
            elif assignment_mode == "save":
                _update_assignment(conn, assignment)
            else:
                raise ValueError(f"unknown assignment_mode {assignment_mode!r}")
            conn.execute(
                text(
                    """
                    UPDATE identity.users SET
                        account_type=:account_type, email=:email,
                        display_name=:display_name, status=:status,
                        authz_version=:authz_version, password_hash=:password_hash,
                        tenant_id=:tenant_id, updated_at=:updated_at,
                        preferred_language=:preferred_language
                    WHERE user_id=:user_id
                    """
                ),
                user.__dict__,
            )
            if change is not None:
                exists = (
                    conn.execute(
                        text(
                            """
                            SELECT 1 FROM identity.privileged_change_requests
                            WHERE change_id = :id
                            """
                        ),
                        {"id": change.change_id},
                    )
                    .mappings()
                    .first()
                )
                if exists:
                    _update_change(conn, change)
                else:
                    _insert_change(conn, change)
            if invitation is not None:
                _update_invitation(conn, invitation)
            if revoke_sessions:
                _revoke_sessions(conn, user.user_id, at)

    def record_delivery_secret(
        self, invitation_id: str, raw_token: str, *, work_email: str
    ) -> None:
        with self._engine.begin() as conn:
            existing = (
                conn.execute(
                    text(
                        """
                        SELECT delivery_id FROM identity.invitation_delivery_outbox
                        WHERE invitation_id = :invitation_id
                        """
                    ),
                    {"invitation_id": invitation_id},
                )
                .mappings()
                .first()
            )
            if existing:
                return
            conn.execute(
                text(
                    """
                    INSERT INTO identity.invitation_delivery_outbox (
                        delivery_id, invitation_id, work_email, raw_token, status, created_at
                    ) VALUES (
                        :delivery_id, :invitation_id, :work_email, :raw_token, 'pending', now()
                    )
                    """
                ),
                {
                    "delivery_id": str(uuid.uuid4()),
                    "invitation_id": invitation_id,
                    "work_email": work_email,
                    "raw_token": raw_token,
                },
            )

    def peek_delivery_secret(self, invitation_id: str) -> str | None:
        with self._engine.connect() as conn:
            row = (
                conn.execute(
                    text(
                        """
                        SELECT raw_token FROM identity.invitation_delivery_outbox
                        WHERE invitation_id = :invitation_id
                        """
                    ),
                    {"invitation_id": invitation_id},
                )
                .mappings()
                .first()
            )
        return str(row["raw_token"]) if row else None

    def list_pending_deliveries(self) -> tuple[DeliveryOutboxItem, ...]:
        with self._engine.connect() as conn:
            rows = (
                conn.execute(
                    text(
                        """
                        SELECT * FROM identity.invitation_delivery_outbox
                        WHERE status = 'pending'
                        ORDER BY created_at ASC
                        """
                    )
                )
                .mappings()
                .all()
            )
        return tuple(_delivery_from_row(r) for r in rows)

    def mark_delivery_delivered(
        self, delivery_id: str, *, acceptance_link: str, at: datetime
    ) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE identity.invitation_delivery_outbox
                    SET status = 'delivered',
                        delivered_at = :at,
                        acceptance_link = :acceptance_link
                    WHERE delivery_id = :delivery_id
                      AND status = 'pending'
                    """
                ),
                {
                    "delivery_id": delivery_id,
                    "acceptance_link": acceptance_link,
                    "at": at,
                },
            )

    def list_sandbox_inbox(
        self, *, work_email: str | None = None
    ) -> tuple[DeliveryOutboxItem, ...]:
        sql = """
            SELECT * FROM identity.invitation_delivery_outbox
            WHERE status = 'delivered'
        """
        params: dict[str, Any] = {}
        if work_email is not None:
            sql += " AND lower(work_email) = lower(:work_email)"
            params["work_email"] = work_email
        sql += " ORDER BY delivered_at DESC NULLS LAST, created_at DESC"
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return tuple(_delivery_from_row(r) for r in rows)

    def append_audit(self, event: AuditEvent) -> AuditEvent:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO identity.identity_audit_events (
                        event_id, actor_user_id, action, target_type, target_id,
                        tenant_id, at, details_json, request_id
                    ) VALUES (
                        :event_id, :actor_user_id, :action, :target_type, :target_id,
                        :tenant_id, :at, :details_json, :request_id
                    )
                    """
                ),
                {
                    **{k: v for k, v in event.__dict__.items() if k != "details"},
                    "details_json": json.dumps(event.details, sort_keys=True),
                },
            )
        return event

    def list_audit(self, *, limit: int = 100) -> tuple[AuditEvent, ...]:
        with self._engine.connect() as conn:
            rows = (
                conn.execute(
                    text(
                        """
                        SELECT * FROM identity.identity_audit_events
                        ORDER BY at DESC LIMIT :limit
                        """
                    ),
                    {"limit": limit},
                )
                .mappings()
                .all()
            )
        return tuple(_audit_from_row(r) for r in rows)


def _revoke_sessions(conn: Any, user_id: str, at: datetime) -> int:
    result = conn.execute(
        text(
            """
            UPDATE identity.sessions SET revoked_at = :at
            WHERE user_id = :user_id AND revoked_at IS NULL
            """
        ),
        {"user_id": user_id, "at": at},
    )
    return int(result.rowcount or 0)


def _insert_assignment(conn: Any, assignment: RoleAssignment) -> None:
    conn.execute(
        text(
            """
            INSERT INTO identity.role_assignments (
                assignment_id, user_id, tenant_id, role_id, scope_key, merchant_ref,
                team_id, status, granted_by, granted_at, revoked_at, grant_review_id
            ) VALUES (
                :assignment_id, :user_id, :tenant_id, :role_id, :scope_key, :merchant_ref,
                :team_id, :status, :granted_by, :granted_at, :revoked_at, :grant_review_id
            )
            """
        ),
        assignment.__dict__,
    )


def _update_assignment(conn: Any, assignment: RoleAssignment) -> None:
    conn.execute(
        text(
            """
            UPDATE identity.role_assignments SET
                status=:status, revoked_at=:revoked_at, merchant_ref=:merchant_ref,
                team_id=:team_id, scope_key=:scope_key, grant_review_id=:grant_review_id
            WHERE assignment_id=:assignment_id
            """
        ),
        assignment.__dict__,
    )


def _insert_invitation(conn: Any, invitation: Invitation) -> None:
    conn.execute(
        text(
            """
            INSERT INTO identity.staff_invitations (
                invitation_id, work_email, display_name, tenant_id,
                role_id, scope_key, token_hash, status, review_state,
                privileged_change_id, invited_by, created_at, expires_at,
                idempotency_key, merchant_ref, team_id, reason,
                accepted_at, revoked_at, accepted_user_id
            ) VALUES (
                :invitation_id, :work_email, :display_name, :tenant_id,
                :role_id, :scope_key, :token_hash, :status, :review_state,
                :privileged_change_id, :invited_by, :created_at, :expires_at,
                :idempotency_key, :merchant_ref, :team_id, :reason,
                :accepted_at, :revoked_at, :accepted_user_id
            )
            """
        ),
        invitation.__dict__,
    )


def _update_invitation(conn: Any, invitation: Invitation) -> None:
    conn.execute(
        text(
            """
            UPDATE identity.staff_invitations SET
                status=:status, review_state=:review_state,
                accepted_at=:accepted_at, revoked_at=:revoked_at,
                accepted_user_id=:accepted_user_id,
                privileged_change_id=:privileged_change_id
            WHERE invitation_id=:invitation_id
            """
        ),
        invitation.__dict__,
    )


def _insert_change(conn: Any, change: PrivilegedChangeRequest) -> None:
    conn.execute(
        text(
            """
            INSERT INTO identity.privileged_change_requests (
                change_id, kind, state, maker_user_id, reviewer_user_id, role_id,
                tenant_id, target_user_id, invitation_id, assignment_id,
                created_at, decided_at, reason, decision_reason
            ) VALUES (
                :change_id, :kind, :state, :maker_user_id, :reviewer_user_id, :role_id,
                :tenant_id, :target_user_id, :invitation_id, :assignment_id,
                :created_at, :decided_at, :reason, :decision_reason
            )
            """
        ),
        change.__dict__,
    )


def _update_change(conn: Any, change: PrivilegedChangeRequest) -> None:
    conn.execute(
        text(
            """
            UPDATE identity.privileged_change_requests SET
                state=:state, reviewer_user_id=:reviewer_user_id,
                decided_at=:decided_at, decision_reason=:decision_reason
            WHERE change_id=:change_id
            """
        ),
        change.__dict__,
    )


def _user_from_row(row: Any) -> User:
    return User(
        user_id=str(row["user_id"]),
        account_type=row["account_type"],
        email=row["email"],
        display_name=row["display_name"],
        status=row["status"],
        authz_version=int(row["authz_version"]),
        password_hash=row["password_hash"],
        created_at=_dt(row["created_at"]),
        updated_at=_dt(row["updated_at"]),
        tenant_id=row["tenant_id"],
        preferred_language=str(row["preferred_language"]) if row.get("preferred_language") else "",
    )


def _assignment_from_row(row: Any) -> RoleAssignment:
    return RoleAssignment(
        assignment_id=str(row["assignment_id"]),
        user_id=str(row["user_id"]),
        tenant_id=row["tenant_id"],
        role_id=row["role_id"],
        scope_key=row["scope_key"],
        status=row["status"],
        granted_by=str(row["granted_by"]) if row["granted_by"] else None,
        granted_at=_dt(row["granted_at"]),
        merchant_ref=row["merchant_ref"],
        team_id=row["team_id"],
        revoked_at=_dt(row["revoked_at"]) if row["revoked_at"] else None,
        grant_review_id=str(row["grant_review_id"]) if row.get("grant_review_id") else None,
    )


def _session_from_row(row: Any) -> SessionRecord:
    return SessionRecord(
        session_id=str(row["session_id"]),
        token_hash=row["token_hash"],
        user_id=str(row["user_id"]),
        assignment_id=str(row["assignment_id"]) if row["assignment_id"] else None,
        authz_version=int(row["authz_version"]),
        issued_at=_dt(row["issued_at"]),
        expires_at=_dt(row["expires_at"]),
        revoked_at=_dt(row["revoked_at"]) if row["revoked_at"] else None,
        mfa_verified_at=_dt(row["mfa_verified_at"]) if row["mfa_verified_at"] else None,
    )


def _invitation_from_row(row: Any) -> Invitation:
    return Invitation(
        invitation_id=str(row["invitation_id"]),
        work_email=row["work_email"],
        display_name=row["display_name"],
        tenant_id=row["tenant_id"],
        role_id=row["role_id"],
        scope_key=row["scope_key"],
        token_hash=row["token_hash"],
        status=row["status"],
        invited_by=str(row["invited_by"]),
        created_at=_dt(row["created_at"]),
        expires_at=_dt(row["expires_at"]),
        idempotency_key=row["idempotency_key"],
        review_state=row.get("review_state") or "not_required",
        privileged_change_id=(
            str(row["privileged_change_id"]) if row.get("privileged_change_id") else None
        ),
        merchant_ref=row["merchant_ref"],
        team_id=row["team_id"],
        reason=row["reason"],
        accepted_at=_dt(row["accepted_at"]) if row["accepted_at"] else None,
        revoked_at=_dt(row["revoked_at"]) if row["revoked_at"] else None,
        accepted_user_id=str(row["accepted_user_id"]) if row["accepted_user_id"] else None,
    )


def _change_from_row(row: Any) -> PrivilegedChangeRequest:
    return PrivilegedChangeRequest(
        change_id=str(row["change_id"]),
        kind=row["kind"],
        state=row["state"],
        maker_user_id=str(row["maker_user_id"]),
        role_id=row["role_id"],
        tenant_id=row["tenant_id"],
        created_at=_dt(row["created_at"]),
        target_user_id=str(row["target_user_id"]) if row["target_user_id"] else None,
        invitation_id=str(row["invitation_id"]) if row["invitation_id"] else None,
        assignment_id=str(row["assignment_id"]) if row["assignment_id"] else None,
        reviewer_user_id=str(row["reviewer_user_id"]) if row["reviewer_user_id"] else None,
        decided_at=_dt(row["decided_at"]) if row["decided_at"] else None,
        reason=row["reason"],
        decision_reason=row["decision_reason"],
    )


def _audit_from_row(row: Any) -> AuditEvent:
    details = row["details_json"]
    if isinstance(details, str):
        details = json.loads(details)
    return AuditEvent(
        event_id=str(row["event_id"]),
        actor_user_id=str(row["actor_user_id"]) if row["actor_user_id"] else None,
        action=row["action"],
        target_type=row["target_type"],
        target_id=row["target_id"],
        tenant_id=row["tenant_id"],
        at=_dt(row["at"]),
        details=details or {},
        request_id=row["request_id"],
    )


def _delivery_from_row(row: Any) -> DeliveryOutboxItem:
    return DeliveryOutboxItem(
        delivery_id=str(row["delivery_id"]),
        invitation_id=str(row["invitation_id"]),
        work_email=row["work_email"],
        raw_token=row["raw_token"],
        status=row["status"],
        created_at=_dt(row["created_at"]),
        delivered_at=_dt(row["delivered_at"]) if row["delivered_at"] else None,
        acceptance_link=row["acceptance_link"],
    )
