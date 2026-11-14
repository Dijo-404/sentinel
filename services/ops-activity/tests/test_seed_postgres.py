"""Postgres OPS_ACTIVITY_DATABASE_URL: seed + list from DB."""

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

from sentinel_ops_activity.adapters.postgres_store import PostgresActivityStore, build_engine
from sentinel_ops_activity.bootstrap import Settings, build_app
from sentinel_ops_activity.seed import (
    SEED_ACTIVITY_ID,
    SEED_CASE_ID,
    SEED_TENANT_ID,
    seed_demo_activity,
)

IMAGE = "postgres:17-alpine@sha256:d3244e8ce3f165ee3c93d9c4a4b1d0fe48b3a89e2287b717fdcbbde92d405065"


def docker(*args: str) -> str:
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"Docker command failed: {result.stderr.strip()}")
    return result.stdout.strip()


@pytest.fixture(scope="module")
def postgres_url():
    name = "sentinel-ops-act-" + secrets.token_hex(6)
    database = "sentinel_ops_act_" + secrets.token_hex(6)
    password = "ops" + secrets.token_hex(12)
    engine = None
    with tempfile.NamedTemporaryFile(mode="w", prefix="ops-act-pg-env-") as env_file:
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


def test_seed_inserts_and_lists_from_postgres(postgres_url: str):
    report = seed_demo_activity(postgres_url)
    assert report["status"] == "PASS"
    assert report["tenant_id"] == SEED_TENANT_ID
    assert report["activity_id"] == SEED_ACTIVITY_ID
    assert report["case_id"] == SEED_CASE_ID

    store = PostgresActivityStore(build_engine(postgres_url))
    items = store.list_activity(SEED_TENANT_ID, limit=50)
    assert any(i.activity_id == SEED_ACTIVITY_ID for i in items)

    again = seed_demo_activity(postgres_url)
    assert again["activity_id"] == SEED_ACTIVITY_ID

    settings = Settings(
        mode="real-peers",
        tokens=_token_map(),
        database_url=postgres_url,
        contract_version="sentinel.task-contracts.v1",
    )
    client = TestClient(build_app(settings))
    response = client.get(
        "/v1/activity",
        headers={"Authorization": "Bearer operator-token"},
    )
    assert response.status_code == 200
    ids = [i["activity_id"] for i in response.json()["items"]]
    assert SEED_ACTIVITY_ID in ids
    seeded = next(i for i in response.json()["items"] if i["activity_id"] == SEED_ACTIVITY_ID)
    assert seeded["kind"]
    assert seeded["summary"]
    assert seeded["occurred_at"]
    assert seeded["case_id"] == SEED_CASE_ID
