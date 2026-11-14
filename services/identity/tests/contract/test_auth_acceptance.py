"""AUTH acceptance tests from docs/roles.md §16.1 (subset for SN-035)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from tests.conftest import NEW_PASSWORD, auth_header, login

from sentinel_identity.adapters.seed import DEMO_PASSWORD
from sentinel_identity.adapters.storage_memory import MemoryIdentityStore
from sentinel_identity.domain.models import RoleAssignment
from sentinel_identity.domain.roles import CONTRACT_VERSION


def test_auth01_register_rejects_privileged_role(client: TestClient) -> None:
    response = client.post(
        "/v1/auth/customer/register",
        json={
            "email": "new-customer@example.test",
            "password": NEW_PASSWORD,
            "display_name": "New Customer",
            "role": "admin",
        },
    )
    assert response.status_code == 422
    users = client.post(
        "/v1/auth/login",
        json={"email": "new-customer@example.test", "password": NEW_PASSWORD},
    )
    assert users.status_code == 401


def test_auth01_clean_register_is_customer_only(client: TestClient) -> None:
    response = client.post(
        "/v1/auth/customer/register",
        json={
            "email": "clean@example.test",
            "password": NEW_PASSWORD,
            "display_name": "Clean Customer",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["account_type"] == "customer"
    assert body["assignment"]["role_id"] == "customer"


def test_auth01_register_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        "/v1/auth/customer/register",
        json={
            "email": "short-pass@example.test",
            "password": "short",
            "display_name": "Short Pass",
        },
    )
    assert response.status_code == 422
    assert "password" in response.json()["message"].lower()


def test_auth02_public_staff_signup_absent(client: TestClient) -> None:
    response = client.post(
        "/v1/auth/customer/register",
        json={
            "email": "wannabe-staff@example.test",
            "password": NEW_PASSWORD,
            "display_name": "Wannabe",
            "account_type": "staff",
            "role_id": "operator",
        },
    )
    assert response.status_code == 422


def test_auth03_invite_accept_replay(
    client: TestClient, demo_password: str, store: MemoryIdentityStore
) -> None:
    admin = login(client, "admin@example.test", demo_password, requested_role="platform_admin")
    invite = client.post(
        "/v1/admin/invitations",
        headers=auth_header(admin["session_token"]),
        json={
            "display_name": "Fresh Operator",
            "work_email": "fresh-op@example.test",
            "tenant_id": "tenant-demo",
            "role_id": "operator",
            "idempotency_key": "invite-fresh-op-001",
            "reason": "onboarding",
        },
    )
    assert invite.status_code == 201
    assert "invite_token" not in invite.json()
    inv_id = invite.json()["invitation"]["invitation_id"]
    token = store.peek_delivery_secret(inv_id)
    assert token
    first = client.post(
        "/v1/auth/accept-invitation",
        json={
            "token": token,
            "email": "fresh-op@example.test",
            "password": NEW_PASSWORD,
            "display_name": "Fresh Operator",
        },
    )
    assert first.status_code == 201
    second = client.post(
        "/v1/auth/accept-invitation",
        json={
            "token": token,
            "email": "fresh-op@example.test",
            "password": NEW_PASSWORD,
        },
    )
    assert second.status_code == 409
    user = store.get_user_by_email("fresh-op@example.test")
    assert user is not None
    active = [a for a in store.list_assignments(user.user_id) if a.status == "active"]
    assert len(active) == 1


def test_auth04_expired_revoked_mismatched_invite(
    client: TestClient, demo_password: str, store: MemoryIdentityStore
) -> None:
    admin = login(client, "admin@example.test", demo_password, requested_role="platform_admin")
    headers = auth_header(admin["session_token"])

    mismatched = client.post(
        "/v1/admin/invitations",
        headers=headers,
        json={
            "display_name": "Mismatch",
            "work_email": "mismatch@example.test",
            "tenant_id": "tenant-demo",
            "role_id": "operator",
            "idempotency_key": "invite-mismatch-001",
        },
    )
    assert mismatched.status_code == 201
    token = store.peek_delivery_secret(mismatched.json()["invitation"]["invitation_id"])
    bad_email = client.post(
        "/v1/auth/accept-invitation",
        json={"token": token, "email": "other@example.test", "password": DEMO_PASSWORD},
    )
    assert bad_email.status_code == 403

    revoked = client.post(
        "/v1/admin/invitations",
        headers=headers,
        json={
            "display_name": "Revoked",
            "work_email": "revoked@example.test",
            "tenant_id": "tenant-demo",
            "role_id": "operator",
            "idempotency_key": "invite-revoked-001",
        },
    )
    assert revoked.status_code == 201
    inv_id = revoked.json()["invitation"]["invitation_id"]
    token = store.peek_delivery_secret(inv_id)
    assert client.post(f"/v1/admin/invitations/{inv_id}/revoke", headers=headers).status_code == 200
    revoked_accept = client.post(
        "/v1/auth/accept-invitation",
        json={"token": token, "email": "revoked@example.test", "password": DEMO_PASSWORD},
    )
    assert revoked_accept.status_code in {403, 409}

    expired = client.post(
        "/v1/admin/invitations",
        headers=headers,
        json={
            "display_name": "Expired",
            "work_email": "expired@example.test",
            "tenant_id": "tenant-demo",
            "role_id": "operator",
            "idempotency_key": "invite-expired-001",
        },
    )
    assert expired.status_code == 201
    inv = store.get_invitation(expired.json()["invitation"]["invitation_id"])
    assert inv is not None
    store.save_invitation(replace(inv, expires_at=datetime.now(UTC) - timedelta(hours=1)))
    assert (
        client.post(
            "/v1/auth/accept-invitation",
            json={
                "token": store.peek_delivery_secret(inv.invitation_id),
                "email": "expired@example.test",
                "password": DEMO_PASSWORD,
            },
        ).status_code
        == 403
    )


def test_auth05_operator_supervisor_role_mismatch(client: TestClient, demo_password: str) -> None:
    response = client.post(
        "/v1/auth/login",
        json={
            "email": "operator@example.test",
            "password": demo_password,
            "requested_role": "supervisor",
        },
    )
    assert response.status_code == 403
    ok = login(client, "operator@example.test", demo_password, requested_role="operator")
    me = client.get("/v1/auth/me", headers=auth_header(ok["session_token"]))
    assert me.status_code == 200
    assert me.json()["active_assignment"]["role_id"] == "operator"


def test_admin_invite_rejects_active_user_email(client: TestClient, demo_password: str) -> None:
    admin = login(client, "admin@example.test", demo_password, requested_role="platform_admin")
    response = client.post(
        "/v1/admin/invitations",
        headers=auth_header(admin["session_token"]),
        json={
            "display_name": "Duplicate Operator",
            "work_email": "operator@example.test",
            "tenant_id": "tenant-demo",
            "role_id": "operator",
            "idempotency_key": "invite-duplicate-operator-001",
            "reason": "should-conflict",
        },
    )
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "CONFLICT"
    assert "invitation" not in body
    assert body["message"] == "Account already exists"


def test_auth11_admin_cannot_invite_customer(client: TestClient, demo_password: str) -> None:
    admin = login(client, "admin@example.test", demo_password, requested_role="platform_admin")
    response = client.post(
        "/v1/admin/invitations",
        headers=auth_header(admin["session_token"]),
        json={
            "display_name": "Nope",
            "work_email": "nope@example.test",
            "tenant_id": "tenant-demo",
            "role_id": "customer",
            "idempotency_key": "invite-customer-denied",
        },
    )
    assert response.status_code == 422
    service = client.post(
        "/v1/admin/invitations",
        headers=auth_header(admin["session_token"]),
        json={
            "display_name": "Nope",
            "work_email": "workflow@example.test",
            "tenant_id": "tenant-demo",
            "role_id": "workflow",
            "idempotency_key": "invite-workflow-denied",
        },
    )
    assert service.status_code == 422


def test_auth12_privileged_invite_needs_independent_review(
    client: TestClient, demo_password: str, store: MemoryIdentityStore
) -> None:
    admin = login(client, "admin@example.test", demo_password, requested_role="platform_admin")
    invite = client.post(
        "/v1/admin/invitations",
        headers=auth_header(admin["session_token"]),
        json={
            "display_name": "New Supervisor",
            "work_email": "new-sup@example.test",
            "tenant_id": "tenant-demo",
            "role_id": "supervisor",
            "idempotency_key": "invite-sup-review-001",
        },
    )
    assert invite.status_code == 201
    body = invite.json()
    assert body["invitation"]["review_state"] == "awaiting_review"
    change_id = body["privileged_change_id"]
    token = store.peek_delivery_secret(body["invitation"]["invitation_id"])
    blocked = client.post(
        "/v1/auth/accept-invitation",
        json={
            "token": token,
            "email": "new-sup@example.test",
            "password": NEW_PASSWORD,
            "display_name": "New Supervisor",
        },
    )
    assert blocked.status_code == 403

    # Maker cannot self-approve.
    self_decide = client.post(
        f"/v1/admin/privileged-changes/{change_id}/decision",
        headers=auth_header(admin["session_token"]),
        json={"decision": "approve"},
    )
    assert self_decide.status_code == 403

    reviewer = login(
        client, "admin-reviewer@example.test", demo_password, requested_role="platform_admin"
    )
    approved = client.post(
        f"/v1/admin/privileged-changes/{change_id}/decision",
        headers=auth_header(reviewer["session_token"]),
        json={"decision": "approve", "reason": "independent review ok"},
    )
    assert approved.status_code == 200
    accepted = client.post(
        "/v1/auth/accept-invitation",
        json={
            "token": token,
            "email": "new-sup@example.test",
            "password": NEW_PASSWORD,
            "display_name": "New Supervisor",
        },
    )
    assert accepted.status_code == 201
    assert accepted.json()["assignment"]["role_id"] == "supervisor"


def test_accept_invitation_rejects_short_password(
    client: TestClient, demo_password: str, store: MemoryIdentityStore
) -> None:
    admin = login(client, "admin@example.test", demo_password, requested_role="platform_admin")
    invite = client.post(
        "/v1/admin/invitations",
        headers=auth_header(admin["session_token"]),
        json={
            "display_name": "Short Pass Op",
            "work_email": "short-op@example.test",
            "tenant_id": "tenant-demo",
            "role_id": "operator",
            "idempotency_key": "invite-short-pass-001",
        },
    )
    assert invite.status_code == 201
    token = store.peek_delivery_secret(invite.json()["invitation"]["invitation_id"])
    response = client.post(
        "/v1/auth/accept-invitation",
        json={
            "token": token,
            "email": "short-op@example.test",
            "password": "tiny",
            "display_name": "Short Pass Op",
        },
    )
    assert response.status_code == 422
    assert "password" in response.json()["message"].lower()


def test_merchant_memberships_lists_seeded_merchant(client: TestClient, demo_password: str) -> None:
    admin = login(client, "admin@example.test", demo_password, requested_role="platform_admin")
    response = client.get(
        "/v1/merchant-memberships",
        params={"tenant_id": "tenant-demo", "merchant_ref": "merchant-demo-1"},
        headers=auth_header(admin["session_token"]),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == CONTRACT_VERSION
    assert len(body["memberships"]) == 1
    row = body["memberships"][0]
    assert row["merchant_ref"] == "merchant-demo-1"
    assert row["tenant_id"] == "tenant-demo"
    assert row["display_name"] == "Demo Merchant"
    assert row["subroles"] == ["admin"]
    assert row["status"] == "active"
    assert row["membership_id"] == row["assignment_id"]


def test_merchant_memberships_forbidden_for_operator(
    client: TestClient, demo_password: str
) -> None:
    op = login(client, "operator@example.test", demo_password, requested_role="operator")
    response = client.get(
        "/v1/merchant-memberships",
        params={"tenant_id": "tenant-demo", "merchant_ref": "merchant-demo-1"},
        headers=auth_header(op["session_token"]),
    )
    assert response.status_code == 403


def test_login_multi_assignment_requires_requested_role(
    client: TestClient, demo_password: str, store: MemoryIdentityStore
) -> None:
    user = store.get_user_by_email("operator@example.test")
    assert user is not None
    existing = store.list_assignments(user.user_id)[0]
    store.create_assignment(
        RoleAssignment(
            assignment_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
            user_id=user.user_id,
            tenant_id=existing.tenant_id,
            role_id="merchant",
            scope_key=f"tenant:{existing.tenant_id}|merchant:merchant-demo-1",
            status="active",
            granted_by=None,
            granted_at=existing.granted_at,
            merchant_ref="merchant-demo-1",
        )
    )
    response = client.post(
        "/v1/auth/login",
        json={"email": "operator@example.test", "password": demo_password},
    )
    assert response.status_code == 409
    assert "session_token" not in response.json()
    ok = login(client, "operator@example.test", demo_password, requested_role="operator")
    assert ok["session_token"]
    assert ok["active_assignment"]["role_id"] == "operator"


def test_auth12_privileged_grant_not_immediately_effective(
    client: TestClient, demo_password: str
) -> None:
    admin = login(client, "admin@example.test", demo_password, requested_role="platform_admin")
    op = login(client, "operator@example.test", demo_password, requested_role="operator")
    grant = client.post(
        f"/v1/admin/users/{op['user']['user_id']}/roles",
        headers=auth_header(admin["session_token"]),
        json={"tenant_id": "tenant-demo", "role_id": "supervisor"},
    )
    assert grant.status_code == 201
    body = grant.json()
    assert body["effective"] is False
    assert body["assignment"]["status"] == "pending"
    change_id = body["privileged_change"]["change_id"]

    # Pending assignment is not a usable workspace.
    me = client.get("/v1/auth/me", headers=auth_header(op["session_token"]))
    # authz not bumped yet — session still valid with operator only
    assert me.status_code == 200
    roles = {w["role_id"] for w in me.json()["workspaces"]}
    assert "supervisor" not in roles

    self_grant = client.post(
        f"/v1/admin/users/{admin['user']['user_id']}/roles",
        headers=auth_header(admin["session_token"]),
        json={"tenant_id": "tenant-demo", "role_id": "risk_officer"},
    )
    assert self_grant.status_code == 403

    reviewer = login(
        client, "admin-reviewer@example.test", demo_password, requested_role="platform_admin"
    )
    decided = client.post(
        f"/v1/admin/privileged-changes/{change_id}/decision",
        headers=auth_header(reviewer["session_token"]),
        json={"decision": "approve"},
    )
    assert decided.status_code == 200
    assert decided.json()["effective"] is True


def test_auth13_revoke_invalidates_session(client: TestClient, demo_password: str) -> None:
    admin = login(client, "admin@example.test", demo_password, requested_role="platform_admin")
    op = login(client, "operator@example.test", demo_password, requested_role="operator")
    op_user_id = op["user"]["user_id"]
    assignment_id = op["active_assignment"]["assignment_id"]
    assert client.get("/v1/auth/me", headers=auth_header(op["session_token"])).status_code == 200
    revoked = client.delete(
        f"/v1/admin/users/{op_user_id}/roles/{assignment_id}",
        headers=auth_header(admin["session_token"]),
    )
    assert revoked.status_code == 200
    denied = client.get("/v1/auth/me", headers=auth_header(op["session_token"]))
    assert denied.status_code in {401, 403}


def test_auth15_forged_role_tenant_headers(client: TestClient, demo_password: str) -> None:
    op = login(client, "operator@example.test", demo_password, requested_role="operator")
    headers = {
        **auth_header(op["session_token"]),
        "X-Role": "platform_admin",
        "X-Tenant-Id": "tenant-other",
    }
    response = client.get("/v1/auth/me", headers=headers)
    assert response.status_code == 403


def test_admin_users_list_staff_only(client: TestClient, demo_password: str) -> None:
    admin = login(client, "admin@example.test", demo_password, requested_role="platform_admin")
    response = client.get("/v1/admin/users", headers=auth_header(admin["session_token"]))
    assert response.status_code == 200
    users = response.json()["users"]
    assert users
    assert all(u["account_type"] == "staff" for u in users)
    assert all(u["email"] != "customer@example.test" for u in users)
