from __future__ import annotations

import os

from fastapi import FastAPI

from sentinel_simulator.adapters.auth import default_token_map
from sentinel_simulator.adapters.bind_safety import (
    assert_loopback_or_non_demo,
    is_loopback_host,
)
from sentinel_simulator.adapters.http import mount_routes
from sentinel_simulator.adapters.memory import InMemoryStore
from sentinel_simulator.adapters.seed import default_seed
from sentinel_simulator.adapters.webhooks import resolve_webhook_hmac_key
from sentinel_simulator.application.service import PaymentSimulator

ALLOWED_MODES = frozenset({"fixture", "real-peers"})
PAYMENT_PROVIDER = "simulator"


def resolve_mode(mode: str | None = None) -> str:
    raw = mode if mode is not None else os.environ.get("SIMULATOR_MODE", "fixture")
    if raw not in ALLOWED_MODES:
        # Never claim live / external provider; fall back to fixture labeling.
        return "fixture"
    return raw


def sandbox_enabled() -> bool:
    return os.environ.get("SIMULATOR_SANDBOX", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def create_app(
    *,
    mode: str | None = None,
    store: InMemoryStore | None = None,
    sandbox: bool | None = None,
) -> FastAPI:
    resolved_mode = resolve_mode(mode)
    seed = default_seed()
    memory = store or InMemoryStore(
        orders=seed.orders,
        payments=seed.payments,
        refunds=seed.refunds,
    )
    is_sandbox = sandbox_enabled() if sandbox is None else sandbox
    bind_host = os.environ.get("SIMULATOR_HOST", "127.0.0.1")
    simulator = PaymentSimulator(
        memory,
        sandbox=is_sandbox,
        webhook_hmac_key=resolve_webhook_hmac_key(),
        merchant_ref=os.environ.get("SIMULATOR_MERCHANT_REF", "merchant-demo"),
    )
    tokens = default_token_map(
        tenant_id=os.environ.get("SIMULATOR_TENANT_ID", "tenant-demo"),
        subject_ref=os.environ.get("SIMULATOR_SUBJECT_REF", "subject-demo-42"),
        case_id=os.environ.get("SIMULATOR_CASE_ID", "case-demo-42"),
        workflow_token=os.environ.get("SIMULATOR_TOKEN_WORKFLOW", "tok-workflow"),
        verifier_token=os.environ.get("SIMULATOR_TOKEN_VERIFIER", "tok-verifier"),
        dispatcher_token=os.environ.get("SIMULATOR_TOKEN_DISPATCHER", "tok-dispatcher"),
        sandbox_admin_token=os.environ.get("SIMULATOR_TOKEN_SANDBOX_ADMIN", "tok-sandbox-admin"),
        include_aliases=is_loopback_host(bind_host),
    )
    assert_loopback_or_non_demo(bind_host, tokens.tokens.keys())
    app = FastAPI(title="sentinel-simulator", version="0.1.0")
    app.state.simulator = simulator
    app.state.store = memory
    app.state.mode = resolved_mode
    app.state.payment_provider = PAYMENT_PROVIDER
    app.state.sandbox = is_sandbox
    mount_routes(
        app,
        simulator=simulator,
        tokens=tokens,
        mode=resolved_mode,
        payment_provider=PAYMENT_PROVIDER,
    )
    return app
