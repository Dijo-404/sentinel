"""Opaque bearer token → Principal map. Headers never establish identity alone."""

from __future__ import annotations

from ..application.errors import UnauthorizedError
from ..domain.types import Principal


def parse_token_map(raw: str) -> dict[str, Principal]:
    """
    token=principal_id|tenant_id|roles
    Entries separated by ';'. Roles are comma-separated.
    """
    mapping: dict[str, Principal] = {}
    if not raw.strip():
        return mapping
    for entry in raw.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        token, _, body = entry.partition("=")
        parts = body.split("|")
        if len(parts) != 3:
            raise ValueError(f"Invalid OPS_ACTIVITY_TOKENS entry for {token!r}")
        principal_id, tenant_id, roles = parts
        mapping[token.strip()] = Principal(
            principal_id=principal_id.strip(),
            tenant_id=tenant_id.strip(),
            roles=tuple(r.strip() for r in roles.split(",") if r.strip()),
        )
    return mapping


class TokenAuthenticator:
    def __init__(self, tokens: dict[str, Principal]):
        self._tokens = tokens

    def authenticate(self, authorization: str | None) -> Principal:
        if not authorization or not authorization.startswith("Bearer "):
            raise UnauthorizedError("Missing bearer token")
        token = authorization.removeprefix("Bearer ").strip()
        principal = self._tokens.get(token)
        if principal is None:
            raise UnauthorizedError("Unknown bearer token")
        return principal
