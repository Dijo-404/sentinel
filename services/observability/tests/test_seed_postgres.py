"""Postgres OBSERVABILITY_DATABASE_URL: seed + list from DB."""

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
from tests.conftest import TOKENS

from sentinel_observability.adapters.postgres_store import PostgresSignalStore, build_engine
from sentinel_observability.bootstrap import Settings, build_app
from sentinel_observability.seed import (
    SEED_SIGNAL_ID,
    SEED_SIGNAL_NAME,
    SEED_TENANT_ID,
    seed_demo_signal,
)

IMAGE = "postgres:17-alpine@sha256:d3244e8ce3f165ee3c93d9c4a4b1d0fe48b3a89e2287b717fdcbbde92d405065"


def docker(*args: str) -> str:
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"Docker command failed: {result.stderr.strip()}")
    return result.stdout.strip()


@pytest.fixture(scope="module")
def postgres_url():
    name = "sentinel-obs-" + secrets.token_hex(6)
    database = "sentinel_obs_" + secrets.token_hex(6)
    password = "obs" + secrets.token_hex(12)
    engine = None
    with tempfile.NamedTemporaryFile(mode="w", prefix="obs-pg-env-") as env_file:
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


def _token_map() -> str:
    parts = []
    for token, principal in TOKENS.items():
        roles = ",".join(principal.roles)
        parts.append(f"{token}={principal.principal_id}|{principal.tenant_id}|{roles}")
    return ";".join(parts)


@pytest.mark.postgres
def test_seed_inserts_and_lists_from_postgres(postgres_url: str):
    report = seed_demo_signal(postgres_url)
    assert report["status"] == "PASS"
    assert report["tenant_id"] == SEED_TENANT_ID
    assert report["signal_id"] == SEED_SIGNAL_ID
    assert report["financial_audit"] is False

    store = PostgresSignalStore(build_engine(postgres_url))
    items = store.list_signals(SEED_TENANT_ID, limit=50)
    assert any(i.signal_id == SEED_SIGNAL_ID for i in items)

    again = seed_demo_signal(postgres_url)
    assert again["signal_id"] == SEED_SIGNAL_ID

    settings = Settings(
        mode="real-peers",
        tokens=_token_map(),
        database_url=postgres_url,
        contract_version="sentinel.task-contracts.v1",
    )
    client = TestClient(build_app(settings))
    response = client.get(
        "/v1/signals",
        headers={"Authorization": "Bearer admin-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["financial_audit"] is False
    ids = [i["signal_id"] for i in body["signals"]]
    assert SEED_SIGNAL_ID in ids
    seeded = next(i for i in body["signals"] if i["signal_id"] == SEED_SIGNAL_ID)
    assert seeded["kind"] == "span"
    assert seeded["name"] == SEED_SIGNAL_NAME
    assert seeded["recorded_at"]

    spans = client.get(
        "/v1/spans",
        headers={"Authorization": "Bearer admin-token"},
    ).json()
    assert spans["financial_audit"] is False
    assert any(s["name"] == SEED_SIGNAL_NAME for s in spans["spans"])
