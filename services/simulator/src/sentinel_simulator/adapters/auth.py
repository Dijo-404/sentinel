from __future__ import annotations

from dataclasses import dataclass

from sentinel_simulator.domain.models import Principal
from sentinel_simulator.domain.rules import Unauthorized


@dataclass(frozen=True)
class TokenMap:
    tokens: dict[str, Principal]

    def resolve(self, authorization: str | None) -> Principal:
        if not authorization or not authorization.startswith("Bearer "):
            raise Unauthorized("Bearer token required")
        token = authorization.removeprefix("Bearer ").strip()
        principal = self.tokens.get(token)
        if principal is None:
            raise Unauthorized("unknown bearer token")
        return principal


def default_token_map(
    *,
    tenant_id: str = "tenant-demo",
    subject_ref: str = "subject-demo-42",
    case_id: str = "case-demo-42",
    workflow_token: str = "tok-workflow",
    verifier_token: str = "tok-verifier",
    dispatcher_token: str = "tok-dispatcher",
    sandbox_admin_token: str = "tok-sandbox-admin",
) -> TokenMap:
    """Canonical sandbox tokens plus legacy *-demo aliases."""
    scope = (subject_ref,)
    cases = (case_id,)
    workflow = Principal(
        principal_id="svc-workflow",
        tenant_id=tenant_id,
        roles=("workflow",),
        subject_refs=scope,
        case_ids=cases,
    )
    verifier = Principal(
        principal_id="svc-verifier",
        tenant_id=tenant_id,
        roles=("verifier",),
        subject_refs=scope,
        case_ids=cases,
    )
    dispatcher = Principal(
        principal_id="svc-dispatcher",
        tenant_id=tenant_id,
        roles=("dispatcher",),
        subject_refs=scope,
        case_ids=cases,
    )
    sandbox_admin = Principal(
        principal_id="svc-sandbox-admin",
        tenant_id=tenant_id,
        roles=("sandbox-admin",),
        subject_refs=scope,
        case_ids=cases,
    )
    tokens = {
        workflow_token: workflow,
        verifier_token: verifier,
        dispatcher_token: dispatcher,
        sandbox_admin_token: sandbox_admin,
        # Legacy aliases (same principals).
        "tok-workflow-demo": workflow,
        "tok-verifier-demo": verifier,
        "tok-dispatcher-demo": dispatcher,
        "tok-sandbox-admin-demo": sandbox_admin,
    }
    return TokenMap(tokens)
