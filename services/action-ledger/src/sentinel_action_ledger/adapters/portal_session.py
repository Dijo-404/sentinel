"""Portal session bearer → Principal via identity.v1 GET /v1/auth/me. Fail closed.

Mirrors (copies, no cross-module import) case-api's identity /me projection.
Static service tokens always win; sessions are tried only when no static token matches.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from sentinel_action_ledger.adapters.auth_tokens import TokenPrincipalMap
from sentinel_action_ledger.domain.errors import (
    ForbiddenError,
    PeerUnavailableError,
    UnauthorizedError,
)
from sentinel_action_ledger.domain.types import Principal

# Only human roles the ledger needs. Never map a portal role to workflow/dispatcher/verifier.
PORTAL_ROLE_MAP = {"supervisor": "supervisor", "operator": "operator"}
IDENTITY_TIMEOUT_SECONDS = 2.0


def principal_from_me(body: Any) -> Principal:
    """Map identity /v1/auth/me body to a ledger Principal (401 malformed, 403 not allowed)."""
    if not isinstance(body, dict):
        raise UnauthorizedError("Identity me response malformed")
    user = body.get("user")
    active = body.get("active_assignment")
    if not isinstance(user, dict) or "active_assignment" not in body:
        raise UnauthorizedError("Identity me response malformed")
    if user.get("status") != "active":
        raise ForbiddenError("Portal user is not active")
    if active is None:
        raise ForbiddenError("No active portal assignment")
    if not isinstance(active, dict):
        raise UnauthorizedError("Identity me response malformed")
    principal_id = user.get("user_id")
    tenant_id = active.get("tenant_id")
    role_id = active.get("role_id")
    for value in (principal_id, tenant_id, role_id):
        if not isinstance(value, str) or not value:
            raise UnauthorizedError("Identity me response malformed")
    if active.get("status", "active") != "active":
        raise ForbiddenError("Portal assignment is not active")
    role = PORTAL_ROLE_MAP.get(role_id)
    if role is None:
        raise ForbiddenError("Portal role not permitted on the ledger")
    # Tenant-wide case/subject scope: identity assignments carry no case lists, and every
    # route still enforces tenant, exact role, and (for decide) digest/revision/policy/expiry.
    return Principal(
        principal_id=principal_id,  # exact human approver recorded as reviewer_id/actor_id
        tenant_id=tenant_id,
        roles=(role,),
        subject_refs=("*",),
        case_ids=("*",),
    )


class HttpPortalSessionResolver:
    """Resolve one session token per request; no cross-request cache."""

    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        if not base_url.strip():
            raise ValueError("LEDGER_IDENTITY_BASE_URL must be non-empty when set")
        self._base = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=IDENTITY_TIMEOUT_SECONDS)

    def resolve(self, token: str) -> Principal:
        try:
            response = self._client.get(
                f"{self._base}/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.HTTPError as exc:
            raise PeerUnavailableError("Identity peer unavailable") from exc
        if response.status_code >= 500:
            raise PeerUnavailableError("Identity peer unavailable")
        if response.status_code == 403:
            # identity.v1 returns 403 for suspended/deactivated users or revoked assignments.
            raise ForbiddenError("Portal user or assignment not active")
        if response.status_code != 200:
            raise UnauthorizedError()
        try:
            body = response.json()
        except ValueError as exc:
            raise UnauthorizedError("Identity me response malformed") from exc
        return principal_from_me(body)


class PortalSessionPrincipalMap(TokenPrincipalMap):
    """Static token map first; on no match, resolve the bearer as an identity portal session."""

    def __init__(self, mapping: dict[str, Principal], sessions: HttpPortalSessionResolver) -> None:
        super().__init__(mapping)
        self._sessions = sessions

    def resolve(self, authorization: str | None) -> Principal:
        try:
            return super().resolve(authorization)
        except UnauthorizedError:
            token = (authorization or "").removeprefix("Bearer ").strip()
            if not authorization or not authorization.startswith("Bearer ") or not token:
                raise
            return self._sessions.resolve(token)


def principal_map_from_environ(mapping: dict[str, Principal]) -> TokenPrincipalMap:
    """LEDGER_IDENTITY_BASE_URL unset/empty → exact static-only behaviour."""
    base_url = os.environ.get("LEDGER_IDENTITY_BASE_URL", "").strip()
    if not base_url:
        return TokenPrincipalMap(mapping)
    return PortalSessionPrincipalMap(mapping, HttpPortalSessionResolver(base_url))
