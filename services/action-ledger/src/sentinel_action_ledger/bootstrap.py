"""Composition root: wire config, store, peers, and HTTP app."""

from __future__ import annotations

import os

from sqlalchemy import create_engine

from sentinel_action_ledger.adapters.auth_tokens import (
    TokenPrincipalMap,
    principals_from_environ,
)
from sentinel_action_ledger.adapters.bind_safety import assert_loopback_or_non_demo
from sentinel_action_ledger.adapters.clock import SystemClock
from sentinel_action_ledger.adapters.evidence_client import HttpEvidenceClient
from sentinel_action_ledger.adapters.http_api import create_app
from sentinel_action_ledger.adapters.ids import SecureIdGenerator
from sentinel_action_ledger.adapters.network_guard import ReservationNetworkGuard
from sentinel_action_ledger.adapters.policy_client import HttpPolicyClient
from sentinel_action_ledger.adapters.postgres import PostgresLedgerStore
from sentinel_action_ledger.application.service import ActionLedgerService
from sentinel_action_ledger.domain.errors import PeerUnavailableError


def build_app(
    *,
    engine=None,
    evidence=None,
    policy=None,
    auth: TokenPrincipalMap | None = None,
    clock=None,
    mode: str | None = None,
    lease_seconds: int | None = None,
    network: ReservationNetworkGuard | None = None,
):
    resolved_mode = mode or os.environ.get("LEDGER_MODE", "fixture")
    # Singleton object is fine: guard state is contextvars (request/task local).
    guard = network or ReservationNetworkGuard()
    if engine is None:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise PeerUnavailableError("DATABASE_URL required")
        engine = create_engine(database_url, pool_pre_ping=True, hide_parameters=True)
    store = PostgresLedgerStore(engine)
    if evidence is None or policy is None:
        if resolved_mode != "real-peers":
            raise PeerUnavailableError("Fixture mode requires injected policy/evidence ports")
        token = os.environ.get("LEDGER_TOKEN_WORKFLOW", "tok-workflow")
        evidence = evidence or HttpEvidenceClient(
            os.environ.get("EVIDENCE_BASE_URL", ""),
            token=token,
            guard=guard,
        )
        policy = policy or HttpPolicyClient(
            os.environ.get("POLICY_BASE_URL", ""),
            token=token,
            guard=guard,
        )
    service = ActionLedgerService(
        store=store,
        clock=clock or SystemClock(),
        ids=SecureIdGenerator(),
        evidence=evidence,
        policy=policy,
        network=guard,
        lease_seconds=lease_seconds or int(os.environ.get("LEDGER_LEASE_SECONDS", "300")),
    )
    if auth is None:
        mapping = principals_from_environ()
        assert_loopback_or_non_demo(os.environ.get("LEDGER_HOST", "127.0.0.1"), mapping.keys())
        token_map = TokenPrincipalMap(mapping)
    else:
        token_map = auth
    return create_app(service=service, auth=token_map, mode=resolved_mode)


def create_preview_app():
    """Uvicorn factory: `uvicorn sentinel_action_ledger.bootstrap:create_preview_app`."""
    return build_app()
