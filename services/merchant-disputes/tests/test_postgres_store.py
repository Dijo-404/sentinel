"""Postgres dispute list/get: rows from DB, not invented fixture aggregates."""

from __future__ import annotations

import os
import secrets
import subprocess
import tempfile
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import OperationalError

from sentinel_merchant_disputes.adapters.storage_postgres import (
    PostgresDisputeStore,
    build_engine,
)
from sentinel_merchant_disputes.bootstrap import Settings, build_app
from sentinel_merchant_disputes.domain.types import DisputeCase

IMAGE = "postgres:17-alpine@sha256:d3244e8ce3f165ee3c93d9c4a4b1d0fe48b3a89e2287b717fdcbbde92d405065"

SEED_DISPUTE = DisputeCase(
    dispute_id="dispute-seed-demo-1",
    tenant_id="tenant-demo",
    merchant_ref="merchant-demo",
    case_id="case-demo-42",
    reason_code="CHARGEBACK_DUPLICATE",
    deadline_at="2026-11-20T12:30:00Z",
    evidence_packet_ids=(),
    status="OPEN",
    order_reference="DEMO-ORDER-42",
    case_revision=1,
)

TOKENS = (
    "operator-token=op-1|tenant-demo|operator|subj-demo-1|case-demo-42|merchant-demo;"
    "supervisor-token=sup-1|tenant-demo|supervisor|subj-demo-1|case-demo-42|merchant-demo"
)


def docker(*args: str) -> str:
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"Docker command failed: {result.stderr.strip()}")
    return result.stdout.strip()


@pytest.fixture(scope="module")
def postgres_url():
    name = "sentinel-md-" + secrets.token_hex(6)
    database = "sentinel_md_" + secrets.token_hex(6)
    password = secrets.token_hex(16)
    engine = None
    with tempfile.NamedTemporaryFile(mode="w", prefix="md-pg-env-") as env_file:
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
            yield url.render_as_string(hide_password=False)
        finally:
            if engine is not None:
                engine.dispose()
            subprocess.run(
                ["docker", "rm", "--force", name],
                capture_output=True,
                timeout=30,
                check=False,
            )


def test_list_and_get_from_postgres(postgres_url: str):
    engine = build_engine(postgres_url)
    store = PostgresDisputeStore(engine)
    store.migrate()
    store.create(SEED_DISPUTE, idempotency_key="seed-demo-1")

    settings = Settings(
        mode="fixture",
        tokens=TOKENS,
        case_api_base_url="",
        case_api_token="",
        evidence_base_url="",
        evidence_token="",
        default_deadline_seconds=604800,
        contract_version="sentinel.task-contracts.v1",
        database_url=postgres_url,
    )
    client = TestClient(build_app(settings))
    headers = {"Authorization": "Bearer operator-token"}

    listed = client.get("/v1/merchants/merchant-demo/disputes", headers=headers)
    assert listed.status_code == 200
    body = listed.json()
    assert body == {
        "disputes": [
            {
                "dispute_id": "dispute-seed-demo-1",
                "tenant_id": "tenant-demo",
                "merchant_ref": "merchant-demo",
                "case_id": "case-demo-42",
                "reason_code": "CHARGEBACK_DUPLICATE",
                "deadline_at": "2026-11-20T12:30:00Z",
                "evidence_packet_ids": [],
                "status": "OPEN",
            }
        ]
    }

    detail = client.get("/v1/disputes/dispute-seed-demo-1", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["dispute_id"] == "dispute-seed-demo-1"
    assert detail.json()["status"] == "OPEN"
    assert detail.json()["tenant_id"] == "tenant-demo"


def test_seed_refuses_non_demo_tenant(postgres_url: str, monkeypatch: pytest.MonkeyPatch):
    from sentinel_merchant_disputes.adapters.seed import seed_sandbox_dispute

    monkeypatch.setenv("DISPUTES_DATABASE_URL", postgres_url)
    monkeypatch.setenv("SENTINEL_V1_SANDBOX", "1")
    monkeypatch.setenv("DISPUTES_TENANT_ID", "tenant-other")
    report = seed_sandbox_dispute(os.environ)
    assert report["status"] == "FAIL"
    assert report["reason_code"] == "SANDBOX_TENANT_REQUIRED"


def test_seed_inserts_open_dispute(postgres_url: str, monkeypatch: pytest.MonkeyPatch):
    from sentinel_merchant_disputes.adapters.seed import seed_sandbox_dispute

    monkeypatch.setenv("DISPUTES_DATABASE_URL", postgres_url)
    monkeypatch.setenv("SENTINEL_V1_SANDBOX", "1")
    monkeypatch.setenv("DISPUTES_TENANT_ID", "tenant-demo")
    report = seed_sandbox_dispute(os.environ)
    assert report["status"] == "PASS"
    assert report["rows"] == 1

    store = PostgresDisputeStore(build_engine(postgres_url))
    loaded = store.get("dispute-seed-demo-1")
    assert loaded is not None
    assert loaded.status == "OPEN"
    assert loaded.tenant_id == "tenant-demo"
