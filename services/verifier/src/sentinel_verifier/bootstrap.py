"""Composition root: wire config, store, peers, and HTTP app."""

from __future__ import annotations

import os

from sqlalchemy import create_engine

from sentinel_verifier.adapters.auth_tokens import TokenPrincipalMap, principals_from_environ
from sentinel_verifier.adapters.bind_safety import assert_loopback_or_non_demo
from sentinel_verifier.adapters.clock import SystemClock
from sentinel_verifier.adapters.http_api import create_app
from sentinel_verifier.adapters.http_peers import (
    HttpCaseApiClient,
    HttpEvidenceClient,
    HttpLedgerClient,
    HttpProviderClient,
)
from sentinel_verifier.adapters.ids import SecureIdGenerator
from sentinel_verifier.adapters.postgres_store import PostgresVerifierStore, ensure_schema
from sentinel_verifier.application.service import VerifierService
from sentinel_verifier.domain.errors import PeerUnavailableError

DEMO_WEBHOOK_HMAC_KEY = "demo-simulator-hmac-key"
DEMO_BEARER_TOKEN = "token-verifier-demo"


def _merchant_map_from_env() -> dict[str, str]:
    raw = os.environ.get("VERIFIER_MERCHANT_MAP", "merchant-demo-1=tenant-demo")
    mapping: dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        merchant, _, tenant = part.partition("=")
        mapping[merchant.strip()] = tenant.strip()
    return mapping


def _resolve_mode(mode: str | None) -> str:
    return mode or os.environ.get("VERIFIER_MODE") or os.environ.get("SENTINEL_MODE") or "fixture"


def _resolve_webhook_hmac_key(*, webhook_hmac_key: str | None, resolved_mode: str) -> str:
    if webhook_hmac_key is not None:
        key = webhook_hmac_key
    else:
        key = os.environ.get("VERIFIER_WEBHOOK_HMAC_KEY")
        if key is None and resolved_mode != "real-peers":
            key = DEMO_WEBHOOK_HMAC_KEY
    if resolved_mode == "real-peers":
        if not key or key == DEMO_WEBHOOK_HMAC_KEY:
            raise PeerUnavailableError("real-peers requires non-demo VERIFIER_WEBHOOK_HMAC_KEY")
    assert key is not None
    return key


def _resolve_peer_bearer(resolved_mode: str) -> str:
    token = os.environ.get("VERIFIER_BEARER_TOKEN")
    if resolved_mode == "real-peers":
        if not token or token == DEMO_BEARER_TOKEN:
            raise PeerUnavailableError("real-peers requires non-demo VERIFIER_BEARER_TOKEN")
        return token
    return token or DEMO_BEARER_TOKEN


def build_app(
    *,
    store=None,
    provider=None,
    ledger=None,
    evidence=None,
    case_api=None,
    auth: TokenPrincipalMap | None = None,
    clock=None,
    ids=None,
    mode: str | None = None,
    webhook_hmac_key: str | None = None,
    merchant_map: dict[str, str] | None = None,
    enforce_event_age: bool = True,
):
    resolved_mode = _resolve_mode(mode)
    resolved_hmac = _resolve_webhook_hmac_key(
        webhook_hmac_key=webhook_hmac_key, resolved_mode=resolved_mode
    )
    if store is None:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise PeerUnavailableError("DATABASE_URL required")
        schema = os.environ.get("VERIFIER_SCHEMA", "verifier")
        engine = create_engine(database_url, pool_pre_ping=True, hide_parameters=True)
        ensure_schema(engine, schema)
        store = PostgresVerifierStore(engine, schema=schema)

    peers = (provider, ledger, evidence, case_api)
    if any(peer is None for peer in peers):
        if resolved_mode != "real-peers":
            raise PeerUnavailableError("Fixture mode requires injected peer ports")
        token = _resolve_peer_bearer(resolved_mode)
        provider = provider or HttpProviderClient(os.environ["PROVIDER_BASE_URL"], token=token)
        ledger = ledger or HttpLedgerClient(os.environ["LEDGER_BASE_URL"], token=token)
        evidence = evidence or HttpEvidenceClient(os.environ["EVIDENCE_BASE_URL"], token=token)
        case_api = case_api or HttpCaseApiClient(os.environ["CASE_API_BASE_URL"], token=token)

    service = VerifierService(
        store=store,
        clock=clock or SystemClock(),
        ids=ids or SecureIdGenerator(),
        provider=provider,
        ledger=ledger,
        evidence=evidence,
        case_api=case_api,
        webhook_hmac_key=resolved_hmac,
        merchant_map=merchant_map or _merchant_map_from_env(),
        enforce_event_age=enforce_event_age,
    )
    if auth is None:
        mapping = principals_from_environ()
        bind_host = os.environ.get("VERIFIER_HOST", "127.0.0.1")
        secrets = [*mapping.keys(), resolved_hmac]
        assert_loopback_or_non_demo(bind_host, secrets)
        token_map = TokenPrincipalMap(mapping)
    else:
        token_map = auth
    return create_app(service=service, auth=token_map, mode=resolved_mode)


def create_preview_app():
    """Uvicorn factory: `uvicorn sentinel_verifier.bootstrap:create_preview_app`."""
    return build_app()
