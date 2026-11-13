"""Synthetic local token → Principal map. Never trust body-supplied identity."""

from __future__ import annotations

from sentinel_verifier.domain.errors import UnauthorizedError
from sentinel_verifier.domain.types import Principal


class TokenPrincipalMap:
    def __init__(self, mapping: dict[str, Principal]) -> None:
        self._mapping = mapping

    def resolve(self, authorization: str | None) -> Principal:
        if not authorization or not authorization.startswith("Bearer "):
            raise UnauthorizedError()
        token = authorization.removeprefix("Bearer ").strip()
        principal = self._mapping.get(token)
        if principal is None:
            raise UnauthorizedError()
        return principal


def demo_principals(tenant_id: str = "tenant-demo") -> dict[str, Principal]:
    """Canonical sandbox tokens plus legacy aliases (integration/core/docs/sandbox-matrix.md)."""
    # Explicit "*" — empty case_ids deny by default.
    cases = ("*",)
    subject = ("subject-demo-1",)
    workflow = Principal("workflow-demo", tenant_id, ("workflow",), subject, cases)
    verifier = Principal("verifier-demo", tenant_id, ("verifier",), (), cases)
    case_api = Principal("case-api-demo", tenant_id, ("workflow",), subject, cases)
    operator = Principal("operator-demo", tenant_id, ("operator",), subject, cases)
    other = Principal("other-tenant", "tenant-other", ("workflow",), subject, cases)
    canonical = {
        "tok-workflow": workflow,
        "tok-verifier": verifier,
        "tok-case-api": case_api,
    }
    aliases = {
        "token-workflow-demo": workflow,
        "token-verifier-demo": verifier,
        "token-case-api-demo": case_api,
        "token-operator-demo": operator,
        "token-other-tenant": other,
    }
    return {**canonical, **aliases}
