"""Composition root: wire config, store, peers, and HTTP app."""

from __future__ import annotations

import os

from sentinel_merchant_refunds.adapters.auth import TokenPrincipalMap, demo_principals
from sentinel_merchant_refunds.adapters.clock import SystemClock
from sentinel_merchant_refunds.adapters.http_api import create_app
from sentinel_merchant_refunds.adapters.http_peers import (
    HttpCaseApiClient,
    HttpEvidenceClient,
    HttpLedgerClient,
    HttpPolicyClient,
)
from sentinel_merchant_refunds.adapters.ids import SecureIdGenerator
from sentinel_merchant_refunds.adapters.memory_store import MemoryRequestStore
from sentinel_merchant_refunds.application.service import MerchantRefundService
from sentinel_merchant_refunds.domain.errors import PeerUnavailableError

DEMO_BEARER_TOKEN = "token-merchant-refunds-demo"


def _resolve_mode(mode: str | None) -> str:
    return (
        mode
        or os.environ.get("MERCHANT_REFUNDS_MODE")
        or os.environ.get("SENTINEL_MODE")
        or "fixture"
    )


def _resolve_peer_bearer(resolved_mode: str) -> str:
    token = os.environ.get("MERCHANT_REFUNDS_PEER_BEARER_TOKEN") or os.environ.get(
        "MERCHANT_REFUNDS_BEARER_TOKEN"
    )
    if resolved_mode == "real-peers":
        if not token or token == DEMO_BEARER_TOKEN:
            raise PeerUnavailableError(
                "real-peers requires non-demo MERCHANT_REFUNDS_PEER_BEARER_TOKEN"
            )
        return token
    return token or DEMO_BEARER_TOKEN


def build_app(
    *,
    store=None,
    case_api=None,
    evidence=None,
    policy=None,
    ledger=None,
    auth: TokenPrincipalMap | None = None,
    clock=None,
    ids=None,
    mode: str | None = None,
):
    resolved_mode = _resolve_mode(mode)
    peers = (case_api, evidence, policy, ledger)
    if any(peer is None for peer in peers):
        if resolved_mode != "real-peers":
            raise PeerUnavailableError("Fixture mode requires injected peer ports")
        token = _resolve_peer_bearer(resolved_mode)
        case_api = case_api or HttpCaseApiClient(os.environ["CASE_API_BASE_URL"], token=token)
        evidence = evidence or HttpEvidenceClient(os.environ["EVIDENCE_BASE_URL"], token=token)
        policy = policy or HttpPolicyClient(os.environ["POLICY_BASE_URL"], token=token)
        ledger = ledger or HttpLedgerClient(os.environ["LEDGER_BASE_URL"], token=token)

    service = MerchantRefundService(
        store=store or MemoryRequestStore(),
        case_api=case_api,
        evidence=evidence,
        policy=policy,
        ledger=ledger,
        clock=clock or SystemClock(),
        ids=ids or SecureIdGenerator(),
    )
    token_map = auth or TokenPrincipalMap(
        demo_principals(
            tenant_id=os.environ.get("MERCHANT_REFUNDS_TENANT_ID", "tenant-demo-1"),
            merchant_ref=os.environ.get("MERCHANT_REFUNDS_MERCHANT_REF", "merchant-demo-1"),
        )
    )
    return create_app(service=service, auth=token_map, mode=resolved_mode)


def create_preview_app():
    """Uvicorn factory for local fixture preview (requires injected env peers)."""
    return build_app()
