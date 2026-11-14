"""Load synthetic fixture principals into an IdentityStore."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from ..application.ports import Clock, IdentityStore
from ..application.security import hash_password, normalize_email
from ..domain.models import Notification, RoleAssignment, User

DEFAULT_SEED = Path(__file__).resolve().parents[3] / "fixtures" / "seed_users.json"

# Low-entropy local-only default. Override with IDENTITY_DEMO_PASSWORD; never commit real secrets.
DEMO_PASSWORD = os.environ.get("IDENTITY_DEMO_PASSWORD", "x")


def load_seed_users(
    store: IdentityStore,
    clock: Clock,
    *,
    path: Path | None = None,
    password: str | None = None,
) -> list[dict]:
    seed_path = path or DEFAULT_SEED
    payload = json.loads(seed_path.read_text(encoding="utf-8"))
    plain = password if password is not None else DEMO_PASSWORD
    now = clock.now()
    loaded: list[dict] = []
    for row in payload["users"]:
        email = normalize_email(row["email"])
        if store.get_user_by_email(email):
            continue
        # JSON seed must not contain plaintext passwords; hash at load time only.
        user = User(
            user_id=row.get("user_id") or str(uuid.uuid4()),
            account_type=row["account_type"],
            email=email,
            display_name=row["display_name"],
            status=row.get("status", "active"),
            authz_version=1,
            password_hash=hash_password(plain),
            created_at=now,
            updated_at=now,
            tenant_id=row["tenant_id"],
            preferred_language=str(row.get("preferred_language", "")),
        )
        store.create_user(user)
        assignment = RoleAssignment(
            assignment_id=row.get("assignment_id") or str(uuid.uuid4()),
            user_id=user.user_id,
            tenant_id=row["tenant_id"],
            role_id=row["role_id"],
            scope_key=row.get("scope_key", f"tenant:{row['tenant_id']}"),
            status="active",
            granted_by=None,
            granted_at=now,
            merchant_ref=row.get("merchant_ref"),
            team_id=row.get("team_id"),
        )
        store.create_assignment(assignment)
        loaded.append(
            {
                "email": user.email,
                "role_id": assignment.role_id,
                "tenant_id": assignment.tenant_id,
                "user_id": user.user_id,
            }
        )
    for row in payload.get("notifications", []):
        notification_id = str(row["notification_id"])
        if store.get_notification(notification_id) is not None:
            continue
        user_id = str(row["user_id"])
        if store.get_user(user_id) is None:
            continue
        store.create_notification(
            Notification(
                notification_id=notification_id,
                user_id=user_id,
                title=str(row["title"]),
                body=str(row["body"]),
                created_at=now,
                read_at=None,
            )
        )
    return loaded
