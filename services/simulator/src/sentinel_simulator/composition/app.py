from __future__ import annotations

import os

from fastapi import FastAPI

from sentinel_simulator.adapters.auth import default_token_map
from sentinel_simulator.adapters.http import mount_routes
from sentinel_simulator.adapters.memory import InMemoryStore
from sentinel_simulator.adapters.seed import demo_orders, demo_payments
from sentinel_simulator.application.service import PaymentSimulator


def create_app(
    *,
    mode: str | None = None,
    store: InMemoryStore | None = None,
) -> FastAPI:
    resolved_mode = mode or os.environ.get("SIMULATOR_MODE", "fixture")
    memory = store or InMemoryStore(orders=demo_orders(), payments=demo_payments())
    simulator = PaymentSimulator(memory)
    tokens = default_token_map(
        tenant_id=os.environ.get("SIMULATOR_TENANT_ID", "tenant-demo"),
        subject_ref=os.environ.get("SIMULATOR_SUBJECT_REF", "subject-demo-42"),
        case_id=os.environ.get("SIMULATOR_CASE_ID", "case-demo-42"),
        workflow_token=os.environ.get("SIMULATOR_TOKEN_WORKFLOW", "tok-workflow"),
        verifier_token=os.environ.get("SIMULATOR_TOKEN_VERIFIER", "tok-verifier"),
        dispatcher_token=os.environ.get("SIMULATOR_TOKEN_DISPATCHER", "tok-dispatcher"),
        sandbox_admin_token=os.environ.get("SIMULATOR_TOKEN_SANDBOX_ADMIN", "tok-sandbox-admin"),
    )
    app = FastAPI(title="sentinel-simulator", version="0.1.0")
    app.state.simulator = simulator
    app.state.store = memory
    mount_routes(app, simulator=simulator, tokens=tokens, mode=resolved_mode)
    return app
