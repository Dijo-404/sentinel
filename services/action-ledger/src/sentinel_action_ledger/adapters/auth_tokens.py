"""Synthetic local token → Principal map. Never trust body-supplied identity."""

from __future__ import annotations

from sentinel_action_ledger.domain.errors import UnauthorizedError
from sentinel_action_ledger.domain.types import Principal


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
    case = ("case-demo-42",)
    subject = ("subject-demo-1",)
    # Empty case_ids deny all; "*" is the explicit broad-access wildcard.
    workflow = Principal("workflow-demo", tenant_id, ("workflow",), subject, case)
    supervisor = Principal("supervisor-demo", tenant_id, ("supervisor",), subject, case)
    dispatcher = Principal("dispatcher-demo", tenant_id, ("dispatcher",), (), ("*",))
    verifier = Principal("verifier-demo", tenant_id, ("verifier",), (), ("*",))
    operator = Principal("operator-demo", tenant_id, ("operator",), subject, case)
    canonical = {
        "tok-workflow": workflow,
        "tok-supervisor": supervisor,
        "tok-dispatcher": dispatcher,
        "tok-verifier": verifier,
    }
    aliases = {
        "token-workflow-demo": workflow,
        "token-supervisor-demo": supervisor,
        "token-dispatcher-demo": dispatcher,
        "token-verifier-demo": verifier,
        "token-operator-demo": operator,
    }
    return {**canonical, **aliases}
