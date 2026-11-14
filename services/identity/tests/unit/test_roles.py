"""Domain role grant invariants."""

from __future__ import annotations

import pytest

from sentinel_identity.domain.roles import (
    EXTENDED_HUMAN_ROLES,
    MONEY_PATH_PERMISSIONS,
    RoleGrantError,
    assert_extended_roles_lack_money_authority,
    assert_staff_role_grantable,
    can_decide_financial_approval,
    permissions_for,
    role_has_money_authority,
)


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


def test_extended_roles_lack_money_authority() -> None:
    assert_extended_roles_lack_money_authority()
    for role in EXTENDED_HUMAN_ROLES:
        assert not role_has_money_authority(role)
        assert not can_decide_financial_approval([role])
        assert permissions_for(role).isdisjoint(MONEY_PATH_PERMISSIONS)


def test_supervisor_alone_may_decide() -> None:
    assert can_decide_financial_approval(["supervisor"])
    assert role_has_money_authority("supervisor")
    assert "financial.approval.decide" in permissions_for("supervisor")
    assert not can_decide_financial_approval(["risk_officer", "platform_admin", "merchant"])
