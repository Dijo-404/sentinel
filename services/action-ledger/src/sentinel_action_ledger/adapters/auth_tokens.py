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


def demo_principals(tenant_id: str = "tenant-demo-1") -> dict[str, Principal]:
    case = ("case-demo-42",)
    subject = ("subject-demo-1",)
    return {
        "token-workflow-demo": Principal("workflow-demo", tenant_id, ("workflow",), subject, case),
        "token-supervisor-demo": Principal(
            "supervisor-demo", tenant_id, ("supervisor",), subject, case
        ),
        "token-dispatcher-demo": Principal("dispatcher-demo", tenant_id, ("dispatcher",), (), case),
        "token-verifier-demo": Principal("verifier-demo", tenant_id, ("verifier",), (), case),
        "token-operator-demo": Principal("operator-demo", tenant_id, ("operator",), subject, case),
    }
