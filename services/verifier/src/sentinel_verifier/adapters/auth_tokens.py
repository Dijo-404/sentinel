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


def demo_principals(tenant_id: str = "tenant-demo-1") -> dict[str, Principal]:
    case = ("case-demo-42",)
    subject = ("subject-demo-1",)
    return {
        "token-workflow-demo": Principal("workflow-demo", tenant_id, ("workflow",), subject, case),
        "token-verifier-demo": Principal("verifier-demo", tenant_id, ("verifier",), (), case),
        "token-case-api-demo": Principal("case-api-demo", tenant_id, ("workflow",), subject, case),
        "token-operator-demo": Principal("operator-demo", tenant_id, ("operator",), subject, case),
        "token-other-tenant": Principal(
            "other-tenant", "tenant-other", ("workflow",), subject, case
        ),
    }
