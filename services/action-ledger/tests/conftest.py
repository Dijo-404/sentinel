"""Private disposable PostgreSQL for ledger proofs."""

from __future__ import annotations

import os
import secrets
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import OperationalError
from tests.stubs.evidence import EvidenceStub
from tests.stubs.policy import PolicyStub

from sentinel_action_ledger.adapters.auth_tokens import TokenPrincipalMap, demo_principals
from sentinel_action_ledger.adapters.clock import FixedClock
from sentinel_action_ledger.adapters.network_guard import ReservationNetworkGuard
from sentinel_action_ledger.bootstrap import build_app

IMAGE = "postgres:17-alpine@sha256:d3244e8ce3f165ee3c93d9c4a4b1d0fe48b3a89e2287b717fdcbbde92d405065"
ROOT = Path(__file__).resolve().parents[1]
DEMO_DIGEST = "d5ce68ac9b173525d7ed0989eeb374cbb41b0a551f4457f8406d85342e1a8993"
DEMO_PAYLOAD = {
    "action": "REQUEST_REFUND",
    "case_id": "case-demo-42",
    "case_revision": 1,
    "transaction_ref": "TXN-B",
    "amount_minor": 150000,
    "currency": "INR",
    "destination": "ORIGINAL_PAYMENT_ROUTE",
    "evidence_ids": ["evidence-payment-b", "evidence-order"],
    "policy_version": "demo-policy-v1",
}


def docker(*args: str) -> str:
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"Docker command failed: {result.stderr.strip()}")
    return result.stdout.strip()


@pytest.fixture(scope="session")
def postgres_url():
    name = "sentinel-sn009-" + secrets.token_hex(6)
    database = "sentinel_ledger_" + secrets.token_hex(6)
    password = secrets.token_urlsafe(24)
    engine = None
    with tempfile.NamedTemporaryFile(mode="w", prefix="sn009-env-") as env_file:
        os.chmod(env_file.name, 0o600)
        env_file.write(f"POSTGRES_PASSWORD={password}\nPOSTGRES_DB={database}\n")
        env_file.flush()
        try:
            docker(
                "run",
                "--detach",
                "--name",
                name,
                "--rm",
                "--publish",
                "127.0.0.1::5432",
                "--tmpfs",
                "/var/lib/postgresql/data:rw,nosuid,size=256m",
                "--env-file",
                env_file.name,
                IMAGE,
            )
            host_port = int(docker("port", name, "5432/tcp").rsplit(":", 1)[1])
            url = URL.create(
                "postgresql+psycopg",
                username="postgres",
                password=password,
                host="127.0.0.1",
                port=host_port,
                database=database,
                query={"connect_timeout": "2"},
            )
            engine = create_engine(url, hide_parameters=True)
            deadline = time.monotonic() + 45
            while True:
                try:
                    with engine.connect() as connection:
                        connection.execute(text("SELECT 1"))
                    break
                except OperationalError:
                    if time.monotonic() >= deadline:
                        raise RuntimeError("Private PostgreSQL did not become ready") from None
                    time.sleep(0.2)
            cfg = Config(str(ROOT / "alembic.ini"))
            cfg.set_main_option("sqlalchemy.url", url.render_as_string(hide_password=False))
            command.upgrade(cfg, "head")
            yield url
        finally:
            if engine is not None:
                engine.dispose()
            subprocess.run(
                ["docker", "rm", "--force", name],
                capture_output=True,
                timeout=30,
                check=False,
            )


@pytest.fixture
def engine(postgres_url):
    eng = create_engine(postgres_url, hide_parameters=True, pool_size=8, max_overflow=4)
    with eng.begin() as connection:
        for table in (
            "outcome_events",
            "financial_audit",
            "outbox",
            "eligibility_snapshots",
            "payment_reservations",
            "approvals",
            "actions",
        ):
            connection.execute(text(f"TRUNCATE {table} CASCADE"))
    yield eng
    eng.dispose()


@pytest.fixture
def clock():
    return FixedClock(datetime(2026, 11, 13, 12, 0, 0, tzinfo=UTC))


@pytest.fixture
def guard():
    return ReservationNetworkGuard()


@pytest.fixture
def app_client(engine, clock, guard):
    evidence = EvidenceStub(guard=guard)
    policy = PolicyStub(guard=guard)
    app = build_app(
        engine=engine,
        evidence=evidence,
        policy=policy,
        auth=TokenPrincipalMap(demo_principals()),
        clock=clock,
        mode="fixture",
        lease_seconds=300,
        network=guard,
    )
    client = TestClient(app)
    client.evidence = evidence
    client.policy = policy
    client.guard = guard
    client.clock = clock
    client.engine = engine
    return client


@pytest.fixture
def tokens():
    return {
        "workflow": "token-workflow-demo",
        "supervisor": "token-supervisor-demo",
        "dispatcher": "token-dispatcher-demo",
        "verifier": "token-verifier-demo",
        "operator": "token-operator-demo",
    }


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def propose_and_approve(client, tokens, *, operation_key="duplicate-demo-42-b", payload=None):
    body_payload = payload or DEMO_PAYLOAD
    digest = DEMO_DIGEST if payload is None else None
    if digest is None:
        from sentinel_action_ledger.domain.digest import action_digest

        digest = action_digest(body_payload)
    proposed = client.post(
        "/v1/actions/proposals",
        headers=auth_header(tokens["workflow"]),
        json={
            "operation_key": operation_key,
            "payload": body_payload,
            "action_digest": digest,
        },
    )
    assert proposed.status_code == 201, proposed.text
    action_id = proposed.json()["action_id"]
    decision = client.post(
        f"/v1/actions/{action_id}/decisions",
        headers=auth_header(tokens["supervisor"]),
        json={
            "decision": "APPROVE",
            "action_digest": digest,
            "case_revision": body_payload["case_revision"],
            "policy_version": body_payload["policy_version"],
            "expires_at": "2026-11-13T13:00:00Z",
        },
    )
    assert decision.status_code == 200, decision.text
    return proposed.json(), decision.json()
