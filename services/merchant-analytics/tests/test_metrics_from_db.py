"""Postgres metrics snapshots: GET serves DB row, not fixture aggregate invention."""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import tempfile
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import OperationalError

from constants import TOKENS, WINDOW
from sentinel_merchant_analytics.adapters.postgres_snapshots import (
    PostgresMetricsSnapshotStore,
    build_engine,
)
from sentinel_merchant_analytics.bootstrap import Settings, build_app
from sentinel_merchant_analytics.domain.types import MerchantMetrics

IMAGE = "postgres:17-alpine@sha256:d3244e8ce3f165ee3c93d9c4a4b1d0fe48b3a89e2287b717fdcbbde92d405065"
ROOT = Path(__file__).resolve().parents[1]

# Deliberately not the fixture expected-metrics aggregate.
DB_SNAPSHOT = {
    "tenant_id": "tenant-demo",
    "merchant_ref": "merchant-demo-1",
    "window_start": WINDOW["window_start"],
    "window_end": WINDOW["window_end"],
    "exception_rate": "0.1234",
    "unresolved_minor": 42,
    "currency": "INR",
    "refund_aging_buckets": {"0-24h": 9, "1-3d": 0, "3-7d": 0, "7d+": 0},
    "median_handling_seconds": 99,
    "top_causes": ["FROM_POSTGRES_SNAPSHOT"],
}


def docker(*args: str) -> str:
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"Docker command failed: {result.stderr.strip()}")
    return result.stdout.strip()


@pytest.fixture(scope="module")
def postgres_url():
    name = "sentinel-ma-" + secrets.token_hex(6)
    database = "sentinel_ma_" + secrets.token_hex(6)
    password = secrets.token_urlsafe(24)
    engine = None
    with tempfile.NamedTemporaryFile(mode="w", prefix="ma-pg-env-") as env_file:
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


def test_metrics_served_from_postgres_snapshot(postgres_url: str):
    engine = build_engine(postgres_url)
    store = PostgresMetricsSnapshotStore(engine)
    store.migrate()
    store.put(
        MerchantMetrics(
            tenant_id=DB_SNAPSHOT["tenant_id"],
            merchant_ref=DB_SNAPSHOT["merchant_ref"],
            window_start=DB_SNAPSHOT["window_start"],
            window_end=DB_SNAPSHOT["window_end"],
            exception_rate=DB_SNAPSHOT["exception_rate"],
            unresolved_minor=DB_SNAPSHOT["unresolved_minor"],
            currency=DB_SNAPSHOT["currency"],
            refund_aging_buckets=dict(DB_SNAPSHOT["refund_aging_buckets"]),
            median_handling_seconds=DB_SNAPSHOT["median_handling_seconds"],
            top_causes=tuple(DB_SNAPSHOT["top_causes"]),
        )
    )

    settings = Settings(
        mode="real-peers",
        tokens=TOKENS,
        case_api_base_url="",
        case_api_token="",
        evidence_base_url="",
        evidence_token="",
        database_url=postgres_url,
        contract_version="sentinel.task-contracts.v1",
    )
    client = TestClient(build_app(settings))
    response = client.get(
        f"/v1/merchants/{DB_SNAPSHOT['merchant_ref']}/metrics",
        params=WINDOW,
        headers={"Authorization": "Bearer operator-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body == DB_SNAPSHOT
    # Prove we did not invent the fixture aggregate.
    fixture = json.loads((ROOT / "contracts" / "expected-metrics.json").read_text(encoding="utf-8"))
    assert body["exception_rate"] != fixture["exception_rate"]
    assert body["unresolved_minor"] != fixture["unresolved_minor"]
    assert body["top_causes"] == ["FROM_POSTGRES_SNAPSHOT"]
