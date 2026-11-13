"""Composition root: wire config, store, peers, and HTTP app."""

from __future__ import annotations

import os

from sqlalchemy import create_engine

from sentinel_verifier.adapters.auth_tokens import TokenPrincipalMap, demo_principals
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


def _merchant_map_from_env() -> dict[str, str]:
    raw = os.environ.get("VERIFIER_MERCHANT_MAP", "merchant-demo-1=tenant-demo-1")
    mapping: dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        merchant, _, tenant = part.partition("=")
        mapping[merchant.strip()] = tenant.strip()
    return mapping


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
    resolved_mode = mode or os.environ.get("VERIFIER_MODE", "fixture")
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
        token = os.environ.get("VERIFIER_BEARER_TOKEN", "token-verifier-demo")
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
        webhook_hmac_key=webhook_hmac_key
        or os.environ.get("VERIFIER_WEBHOOK_HMAC_KEY", "demo-simulator-hmac-key"),
        merchant_map=merchant_map or _merchant_map_from_env(),
        enforce_event_age=enforce_event_age,
    )
    token_map = auth or TokenPrincipalMap(
        demo_principals(os.environ.get("VERIFIER_TENANT_ID", "tenant-demo-1"))
    )
    return create_app(service=service, auth=token_map, mode=resolved_mode)


def create_preview_app():
    """Uvicorn factory: `uvicorn sentinel_verifier.bootstrap:create_preview_app`."""
    return build_app()
