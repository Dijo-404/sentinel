"""Local peer doubles: valid, unavailable, malformed, unauthorized_or_out_of_scope."""

from __future__ import annotations

from .action_ledger import action_ledger_stub
from .case_api import case_api_stub
from .dispatcher import dispatcher_stub
from .identity import identity_stub
from .payment_provider import payment_provider_stub
from .risk import risk_stub
from .verifier import verifier_stub
from .web_shell import web_shell_stub
from .workflow import workflow_stub

STUB_CASES = ("valid", "unavailable", "malformed", "unauthorized_or_out_of_scope")

PEER_FACTORIES = {
    "case-api.v1": case_api_stub,
    "workflow.v1": workflow_stub,
    "action-ledger.v1": action_ledger_stub,
    "dispatcher.v1": dispatcher_stub,
    "verifier.v1": verifier_stub,
    "identity.v1": identity_stub,
    "risk.v1": risk_stub,
    "payment-provider.v1": payment_provider_stub,
    "web-shell.v1": web_shell_stub,
}


def build_stub(port: str, case: str = "valid"):
    if case not in STUB_CASES:
        raise ValueError(f"Unknown stub case: {case}")
    return PEER_FACTORIES[port](case)


__all__ = [
    "STUB_CASES",
    "PEER_FACTORIES",
    "build_stub",
    "case_api_stub",
    "workflow_stub",
    "action_ledger_stub",
    "dispatcher_stub",
    "verifier_stub",
    "identity_stub",
    "risk_stub",
    "payment_provider_stub",
    "web_shell_stub",
]
