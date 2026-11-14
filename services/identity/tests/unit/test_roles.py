"""Domain role grant invariants."""

from __future__ import annotations

import pytest

from sentinel_identity.domain.roles import RoleGrantError, assert_staff_role_grantable


def test_deny_customer_staff_grant() -> None:
    with pytest.raises(RoleGrantError, match="customer"):
        assert_staff_role_grantable("customer")


@pytest.mark.parametrize("role", ["workflow", "dispatcher", "verifier", "sandbox-admin"])
def test_deny_service_roles(role: str) -> None:
    with pytest.raises(RoleGrantError, match="service"):
        assert_staff_role_grantable(role)


@pytest.mark.parametrize(
    "role", ["merchant", "operator", "supervisor", "risk_officer", "platform_admin"]
)
def test_staff_invitable_ok(role: str) -> None:
    assert_staff_role_grantable(role)
