"""Composition root: wire adapters once."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine

from sentinel_api.adapters.bind_safety import assert_loopback_or_non_demo
from sentinel_api.adapters.db.repository import SqlCaseRepository
from sentinel_api.adapters.db.schema import metadata
from sentinel_api.adapters.http.app import create_app
from sentinel_api.adapters.http.auth import TokenMap
from sentinel_api.adapters.peers.fixture_clients import (
    FixtureEvidenceClient,
    FixtureLedgerClient,
    FixtureVerifierClient,
    FixtureWorkflowClient,
)
from sentinel_api.adapters.peers.http_clients import (
    HttpEvidenceClient,
    HttpLedgerClient,
    HttpVerifierClient,
    HttpWorkflowClient,
)
from sentinel_api.application.service import CaseService
from sentinel_api.config import Settings


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class SecureIds:
    def new_id(self, prefix: str) -> str:
        return f"{prefix}-{secrets.token_hex(8)}"


def build_app(settings: Settings | None = None, *, engine=None, tokens: TokenMap | None = None):
    settings = settings or Settings()
    if settings.mode not in {"fixture", "real-peers"}:
        raise ValueError("SENTINEL_API_MODE must be fixture or real-peers")

    module_root = Path(__file__).resolve().parents[2]
    token_map = tokens or TokenMap.from_path(settings.token_path(module_root))
    assert_loopback_or_non_demo(
        settings.host,
        [*token_map.tokens.keys(), settings.service_token],
    )

    if engine is None:
        engine = create_engine(settings.database_url, pool_pre_ping=True, hide_parameters=True)
        metadata.create_all(engine)

    repo = SqlCaseRepository(engine)

    if settings.mode == "fixture":
        workflow: object = FixtureWorkflowClient()
        evidence: object = FixtureEvidenceClient()
        ledger: object = FixtureLedgerClient()
        verifier: object = FixtureVerifierClient()
    else:
        workflow = HttpWorkflowClient(settings.workflow_base_url)
        evidence = HttpEvidenceClient(settings.evidence_base_url)
        ledger = HttpLedgerClient(settings.ledger_base_url)
        verifier = HttpVerifierClient(settings.verifier_base_url)

    service = CaseService(
        repo=repo,
        clock=SystemClock(),
        ids=SecureIds(),
        workflow=workflow,  # type: ignore[arg-type]
        evidence=evidence,  # type: ignore[arg-type]
        ledger=ledger,  # type: ignore[arg-type]
        verifier=verifier,  # type: ignore[arg-type]
        service_authorization=f"Bearer {settings.service_token}",
    )

    def readiness() -> dict:
        peers = {
            "workflow": settings.mode == "fixture" or bool(settings.workflow_base_url),
            "evidence": settings.mode == "fixture" or bool(settings.evidence_base_url),
            "action-ledger": settings.mode == "fixture" or bool(settings.ledger_base_url),
            "verifier": settings.mode == "fixture" or bool(settings.verifier_base_url),
        }
        try:
            repo.ping()
            db_ok = True
        except Exception:
            db_ok = False
        ready = db_ok and all(peers.values())
        return {
            "ready": ready,
            "mode": settings.mode,
            "database": "ok" if db_ok else "unavailable",
            "peers": peers,
            "label": "fixture-local" if settings.mode == "fixture" else "real-peers",
        }

    app = create_app(
        service=service,
        tokens=token_map,
        mode=settings.mode,
        readiness=readiness,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.repo = repo
    app.state.workflow = workflow
    app.state.evidence = evidence
    app.state.ledger = ledger
    app.state.verifier = verifier
    return app


app = None


def get_app():
    global app
    if app is None:
        app = build_app()
    return app
