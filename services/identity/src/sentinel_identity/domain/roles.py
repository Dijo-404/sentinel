"""Canonical role catalog and grant invariants."""

from __future__ import annotations

CONTRACT_VERSION = "sentinel.task-contracts.v1"
CONTRACT_SHA256 = "0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb"

HUMAN_ROLES = frozenset(
    {
        "customer",
        "merchant",
        "operator",
        "supervisor",
        "risk_officer",
        "platform_admin",
    }
)

SERVICE_ROLES = frozenset(
    {
        "workflow",
        "dispatcher",
        "verifier",
        "sandbox-admin",
    }
)

# Platform Admin may invite these staff paths (never customer / service).
STAFF_INVITABLE_ROLES = frozenset(
    {
        "merchant",
        "operator",
        "supervisor",
        "risk_officer",
        "platform_admin",
    }
)

PRIVILEGED_ROLES = frozenset({"supervisor", "risk_officer", "platform_admin"})

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "customer": frozenset({"identity.self.read"}),
    "merchant": frozenset({"identity.self.read", "merchant.workspace.read"}),
    "operator": frozenset({"identity.self.read", "ops.queue.read"}),
    "supervisor": frozenset({"identity.self.read", "ops.queue.read", "approval.decide"}),
    "risk_officer": frozenset({"identity.self.read", "risk.investigate"}),
    "platform_admin": frozenset(
        {
            "identity.self.read",
            "identity.staff.manage",
            "identity.staff.invite",
            "identity.role.grant",
            "identity.role.revoke",
            "identity.audit.read",
            "identity.session.revoke",
        }
    ),
}


class RoleGrantError(ValueError):
    """Raised when a role assignment violates account-class or catalog rules."""


def assert_staff_role_grantable(role_id: str) -> None:
    if role_id == "customer":
        raise RoleGrantError("customer role cannot be granted via staff invite or grant")
    if role_id in SERVICE_ROLES:
        raise RoleGrantError("service roles cannot be assigned to human accounts")
    if role_id not in STAFF_INVITABLE_ROLES:
        raise RoleGrantError(f"role_id {role_id!r} is not staff-invitable")


def permissions_for(role_id: str) -> frozenset[str]:
    return ROLE_PERMISSIONS.get(role_id, frozenset())
