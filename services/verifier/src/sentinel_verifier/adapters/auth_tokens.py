"""Synthetic local token → Principal map. Never trust body-supplied identity."""

from __future__ import annotations

import os

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


def demo_principals(
    tenant_id: str = "tenant-demo",
    *,
    include_aliases: bool = True,
    workflow_token: str = "tok-workflow",
    verifier_token: str = "tok-verifier",
    case_api_token: str = "tok-case-api",
) -> dict[str, Principal]:
    """Canonical sandbox tokens; legacy aliases only when include_aliases is true."""
    # Explicit "*" — empty case_ids deny by default.
    cases = ("*",)
    subject = ("subject-demo-1",)
    workflow = Principal("workflow-demo", tenant_id, ("workflow",), subject, cases)
    verifier = Principal("verifier-demo", tenant_id, ("verifier",), (), cases)
    case_api = Principal("case-api-demo", tenant_id, ("workflow",), subject, cases)
    operator = Principal("operator-demo", tenant_id, ("operator",), subject, cases)
    other = Principal("other-tenant", "tenant-other", ("workflow",), subject, cases)
    canonical = {
        workflow_token: workflow,
        verifier_token: verifier,
        case_api_token: case_api,
    }
    if not include_aliases:
        return canonical
    aliases = {
        "token-workflow-demo": workflow,
        "token-verifier-demo": verifier,
        "token-case-api-demo": case_api,
        "token-operator-demo": operator,
        "token-other-tenant": other,
    }
    return {**canonical, **aliases}


def principals_from_environ(tenant_id: str | None = None) -> dict[str, Principal]:
    from sentinel_verifier.adapters.bind_safety import is_loopback_host

    host = os.environ.get("VERIFIER_HOST", "127.0.0.1")
    return demo_principals(
        tenant_id or os.environ.get("VERIFIER_TENANT_ID", "tenant-demo"),
        include_aliases=is_loopback_host(host),
        workflow_token=os.environ.get("VERIFIER_TOKEN_WORKFLOW", "tok-workflow"),
        verifier_token=os.environ.get("VERIFIER_TOKEN_VERIFIER", "tok-verifier"),
        case_api_token=os.environ.get("VERIFIER_TOKEN_CASE_API", "tok-case-api"),
    )
