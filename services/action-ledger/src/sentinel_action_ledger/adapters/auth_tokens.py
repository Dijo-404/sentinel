"""Synthetic local token → Principal map. Never trust body-supplied identity."""

from __future__ import annotations

import os

from sentinel_action_ledger.domain.errors import UnauthorizedError
from sentinel_action_ledger.domain.types import Principal


class TokenPrincipalMap:
    def __init__(self, mapping: dict[str, Principal]) -> None:
        self._mapping = mapping

    @property
    def tokens(self) -> dict[str, Principal]:
        return self._mapping

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
    workflow_token: str | None = None,
    supervisor_token: str | None = None,
    dispatcher_token: str | None = None,
    verifier_token: str | None = None,
) -> dict[str, Principal]:
    """Canonical sandbox tokens; legacy aliases only when include_aliases is true."""
    case = ("case-demo-42",)
    subject = ("subject-demo-1",)
    # Empty case_ids deny all; "*" is the explicit broad-access wildcard.
    workflow = Principal("workflow-demo", tenant_id, ("workflow",), subject, case)
    supervisor = Principal("supervisor-demo", tenant_id, ("supervisor",), subject, case)
    dispatcher = Principal("dispatcher-demo", tenant_id, ("dispatcher",), (), ("*",))
    verifier = Principal("verifier-demo", tenant_id, ("verifier",), (), ("*",))
    operator = Principal("operator-demo", tenant_id, ("operator",), subject, case)
    # SN-040: catalog entries for new human roles — never supervisor / money roles.
    merchant = Principal("merchant-demo", tenant_id, ("merchant",), subject, case)
    risk_officer = Principal("risk-officer-demo", tenant_id, ("risk_officer",), subject, case)
    platform_admin = Principal(
        "platform-admin-demo", tenant_id, ("platform_admin",), ("*",), ("*",)
    )
    canonical = {
        workflow_token or "tok-workflow": workflow,
        supervisor_token or "tok-supervisor": supervisor,
        dispatcher_token or "tok-dispatcher": dispatcher,
        verifier_token or "tok-verifier": verifier,
    }
    if not include_aliases:
        return canonical
    aliases = {
        "token-workflow-demo": workflow,
        "token-supervisor-demo": supervisor,
        "token-dispatcher-demo": dispatcher,
        "token-verifier-demo": verifier,
        "token-operator-demo": operator,
        "token-merchant-demo": merchant,
        "token-risk-officer-demo": risk_officer,
        "token-platform-admin-demo": platform_admin,
        "tok-merchant": merchant,
        "tok-risk-officer": risk_officer,
        "tok-platform-admin": platform_admin,
    }
    return {**canonical, **aliases}


def principals_from_environ(tenant_id: str | None = None) -> dict[str, Principal]:
    """Build inbound map from LEDGER_TOKEN_* env; drop aliases off loopback."""
    from sentinel_action_ledger.adapters.bind_safety import is_loopback_host

    host = os.environ.get("LEDGER_HOST", "127.0.0.1")
    return demo_principals(
        tenant_id or os.environ.get("LEDGER_TENANT_ID", "tenant-demo"),
        include_aliases=is_loopback_host(host),
        workflow_token=os.environ.get("LEDGER_TOKEN_WORKFLOW"),
        supervisor_token=os.environ.get("LEDGER_TOKEN_SUPERVISOR"),
        dispatcher_token=os.environ.get("LEDGER_TOKEN_DISPATCHER"),
        verifier_token=os.environ.get("LEDGER_TOKEN_VERIFIER"),
    )
