"""Resource authorization from authenticated Principal only."""

from __future__ import annotations

from sentinel_api.domain.types import DomainError, Principal


def require_roles(principal: Principal, *roles: str) -> None:
    if not principal.has_role(*roles):
        raise DomainError("FORBIDDEN", "Principal lacks required role", 403)


def can_access_case(
    principal: Principal,
    *,
    tenant_id: str,
    case_id: str,
    subject_ref: str,
) -> bool:
    if principal.tenant_id != tenant_id:
        return False
    if principal.has_role("customer"):
        if case_id in principal.case_ids:
            return True
        return subject_ref in principal.subject_refs
    if principal.has_role("operator", "supervisor"):
        return True
    if principal.has_role("workflow", "verifier"):
        # Empty case_ids deny; "*" grants all cases in tenant.
        if "*" not in principal.case_ids and case_id not in principal.case_ids:
            return False
        if principal.subject_refs and subject_ref not in principal.subject_refs:
            return False
        return True
    return False


def require_case_access(
    principal: Principal,
    *,
    tenant_id: str,
    case_id: str,
    subject_ref: str,
) -> None:
    if not can_access_case(
        principal, tenant_id=tenant_id, case_id=case_id, subject_ref=subject_ref
    ):
        # Do not leak existence across tenants/scopes.
        raise DomainError("NOT_FOUND", "Case not found", 404)
