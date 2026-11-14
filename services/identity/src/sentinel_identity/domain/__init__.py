"""Framework-free identity domain types and invariants."""

from __future__ import annotations

from .models import (
    AuditEvent,
    Invitation,
    PrivilegedChangeRequest,
    RoleAssignment,
    SessionRecord,
    User,
)
from .roles import (
    CONTRACT_VERSION,
    HUMAN_ROLES,
    SERVICE_ROLES,
    STAFF_INVITABLE_ROLES,
    assert_staff_role_grantable,
)

__all__ = [
    "AuditEvent",
    "CONTRACT_VERSION",
    "HUMAN_ROLES",
    "Invitation",
    "PrivilegedChangeRequest",
    "RoleAssignment",
    "SERVICE_ROLES",
    "STAFF_INVITABLE_ROLES",
    "SessionRecord",
    "User",
    "assert_staff_role_grantable",
]
