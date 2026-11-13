"""Single composition entry point for fixture and real-peer modes."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from sqlalchemy import create_engine

from sentinel_dispatcher.adapters.clock import SystemClock
from sentinel_dispatcher.adapters.http_peers import HttpLedgerClient, HttpProviderClient
from sentinel_dispatcher.adapters.postgres_store import PostgresWorkerStore, ensure_schema
from sentinel_dispatcher.application.worker import DispatchWorker

CONTRACT_VERSION = "sentinel.task-contracts.v1"
CONTRACT_HASH = "0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb"


@dataclass
class App:
    worker: DispatchWorker
    mode: str
    closeables: list[Any]

    def close(self) -> None:
        for item in self.closeables:
            close = getattr(item, "close", None)
            if callable(close):
                close()
            dispose = getattr(item, "dispose", None)
            if callable(dispose):
                dispose()


def resolve_mode(mode: str | None = None) -> str:
    resolved = mode or os.environ.get("DISPATCHER_MODE", "fixture")
    if resolved not in {"fixture", "real-peers"}:
        raise ValueError("DISPATCHER_MODE must be fixture or real-peers")
    return resolved


def capabilities(*, mode: str = "fixture") -> dict[str, str]:
    resolved = resolve_mode(mode)
    return {
        "contract_version": CONTRACT_VERSION,
        "component": "dispatcher",
        "mode": resolved,
        "port": "dispatcher.v1",
        "contract_sha256": CONTRACT_HASH,
    }


def build_http_app(*, mode: str | None = None):
    """Probe surface only. Worker path remains CLI run-once / recover."""
    from sentinel_dispatcher.adapters.http_api import create_app

    return create_app(mode=resolve_mode(mode))


def create_preview_app():
    """Uvicorn factory: listen 127.0.0.1:8010 by default via make preview."""
    return build_http_app()


def build_real_peer_app_from_env() -> App:
    mode = resolve_mode(os.environ.get("DISPATCHER_MODE", "real-peers"))
    if mode == "fixture":
        raise RuntimeError("DISPATCHER_MODE=fixture cannot build real-peer adapters")
    database_url = os.environ["DATABASE_URL"]
    schema = os.environ.get("DISPATCHER_SCHEMA", "dispatcher")
    tenant_id = os.environ["DISPATCHER_TENANT_ID"]
    token = os.environ["DISPATCHER_BEARER_TOKEN"]
    ledger_url = os.environ["LEDGER_BASE_URL"]
    provider_url = os.environ["PROVIDER_BASE_URL"]

    engine = create_engine(database_url, hide_parameters=True)
    ensure_schema(engine, schema)
    store = PostgresWorkerStore(engine, schema=schema)
    ledger = HttpLedgerClient(ledger_url, token=token)
    provider = HttpProviderClient(provider_url, token=token)
    worker = DispatchWorker(
        tenant_id=tenant_id,
        ledger=ledger,
        provider=provider,
        store=store,
        clock=SystemClock(),
    )
    return App(worker=worker, mode="real-peers", closeables=[ledger, provider, engine])
