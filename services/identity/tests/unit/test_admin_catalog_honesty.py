"""Admin catalogs must not invent tenant/team rows absent from the store."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sentinel_identity.adapters.storage_memory import MemoryIdentityStore
from sentinel_identity.application.security import hash_password
from sentinel_identity.application.service import IdentityService
from sentinel_identity.domain.models import RoleAssignment, User


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 11, 15, 12, 0, 0, tzinfo=UTC)


def test_admin_catalogs_reflect_store_only() -> None:
    store = MemoryIdentityStore()
    clock = _Clock()
    service = IdentityService(store=store, clock=clock)
    now = clock.now()
    user = User(
        user_id="admin-1",
        account_type="staff",
        email="admin@example.test",
        display_name="Admin",
        status="active",
        authz_version=1,
        password_hash=hash_password("password12345"),
        created_at=now,
        updated_at=now,
        tenant_id="tenant-real",
    )
    store.create_user(user)
    store.create_assignment(
        RoleAssignment(
            assignment_id="asg-admin",
            user_id=user.user_id,
            tenant_id="tenant-real",
            role_id="platform_admin",
            scope_key="tenant:tenant-real",
            status="active",
            granted_by=None,
            granted_at=now,
            team_id=None,
        )
    )
    login = service.login(
        email="admin@example.test",
        password="password12345",
        requested_role="platform_admin",
    )
    token = login["session_token"]

    tenants = service.admin_list_tenants(session_token=token)["tenants"]
    assert [row["tenant_id"] for row in tenants] == ["tenant-real"]
    assert "tenant-demo" not in {row["tenant_id"] for row in tenants}

    teams = service.admin_list_teams(session_token=token)["teams"]
    assert teams == []
    assert "sandbox-ops" not in {row["team_id"] for row in teams}


def test_admin_teams_include_assignment_team_only() -> None:
    store = MemoryIdentityStore()
    clock = _Clock()
    service = IdentityService(store=store, clock=clock)
    now = clock.now()
    user = User(
        user_id="admin-2",
        account_type="staff",
        email="admin2@example.test",
        display_name="Admin Two",
        status="active",
        authz_version=1,
        password_hash=hash_password("password12345"),
        created_at=now,
        updated_at=now,
        tenant_id="tenant-real",
    )
    store.create_user(user)
    store.create_assignment(
        RoleAssignment(
            assignment_id="asg-admin-2",
            user_id=user.user_id,
            tenant_id="tenant-real",
            role_id="platform_admin",
            scope_key="tenant:tenant-real|team:payments-support",
            status="active",
            granted_by=None,
            granted_at=now,
            team_id="payments-support",
        )
    )
    # Expired session clock still fine for login mint.
    _ = timedelta(hours=1)
    token = service.login(
        email="admin2@example.test",
        password="password12345",
        requested_role="platform_admin",
    )["session_token"]
    teams = service.admin_list_teams(session_token=token)["teams"]
    assert [row["team_id"] for row in teams] == ["payments-support"]
    assert teams[0]["member_count"] == 1
