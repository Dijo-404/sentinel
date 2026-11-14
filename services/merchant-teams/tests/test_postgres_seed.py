"""Postgres staff store: seed merchant-demo-1 membership; list API serves DB rows."""

from __future__ import annotations

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

from sentinel_merchant_teams.adapters.storage_postgres import (
    PostgresStaffStore,
    build_engine,
    seed_merchant_demo_membership,
)
from sentinel_merchant_teams.bootstrap import Settings, build_app

IMAGE = "postgres:17-alpine@sha256:d3244e8ce3f165ee3c93d9c4a4b1d0fe48b3a89e2287b717fdcbbde92d405065"
ROOT = Path(__file__).resolve().parents[1]
TOKENS = (
    "operator-token=op-1|tenant-demo|operator|merchant-demo-1|case-demo-42;"
    "supervisor-token=sup-1|tenant-demo|supervisor|merchant-demo-1,*|case-demo-42"
)


def docker(*args: str) -> str:
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"Docker command failed: {result.stderr.strip()}")
    return result.stdout.strip()


@pytest.fixture(scope="module")
def postgres_url():
    name = "sentinel-mt-" + secrets.token_hex(6)
    database = "sentinel_mt_" + secrets.token_hex(6)
    password = secrets.token_urlsafe(24)
    engine = None
    with tempfile.NamedTemporaryFile(mode="w", prefix="mt-pg-env-") as env_file:
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


@pytest.mark.postgres
def test_seed_membership_served_by_list_api(postgres_url: str):
    report = seed_merchant_demo_membership(postgres_url)
    assert report["status"] == "PASS"
    assert report["tenant_id"] == "tenant-demo"
    assert report["merchant_ref"] == "merchant-demo-1"
    assert report["staff_id"] == "staff-demo-1"

    settings = Settings(
        mode="real-peers",
        tokens=TOKENS,
        case_api_base_url="http://127.0.0.1:9",
        case_api_token="unused-for-list",
        identity_base_url="",
        identity_token="",
        database_url=postgres_url,
        contract_version="sentinel.task-contracts.v1",
    )
    # Inject stub case peer so real-peers bootstrap does not dial HTTP for list path.
    from sentinel_merchant_teams.adapters.case_api_stub import StubCaseApi

    client = TestClient(build_app(settings, cases=StubCaseApi(mode="valid"), identity=None))
    response = client.get(
        "/v1/merchant/team",
        params={"merchant_ref": "merchant-demo-1"},
        headers={"Authorization": "Bearer operator-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "local_projection"
    assert len(body["staff"]) == 1
    staff = body["staff"][0]
    assert staff["staff_id"] == "staff-demo-1"
    assert staff["tenant_id"] == "tenant-demo"
    assert staff["merchant_ref"] == "merchant-demo-1"
    assert staff["display_name"] == "Ada Merchant"
    assert staff["roles"] == ["operator", "approver"]
    assert staff["active"] is True
    assert staff["approval_limit_minor"] == 50000
    assert staff["currency"] == "INR"

    listed = client.get(
        "/v1/staff",
        params={"merchant_ref": "merchant-demo-1"},
        headers={"Authorization": "Bearer operator-token"},
    )
    assert listed.status_code == 200
    assert listed.json()["staff"][0]["staff_id"] == "staff-demo-1"


@pytest.mark.postgres
def test_seed_is_idempotent(postgres_url: str):
    first = seed_merchant_demo_membership(postgres_url)
    second = seed_merchant_demo_membership(postgres_url)
    assert first["status"] == "PASS"
    assert second["status"] == "PASS"
    store = PostgresStaffStore(build_engine(postgres_url))
    rows = store.list_for_merchant(tenant_id="tenant-demo", merchant_ref="merchant-demo-1")
    assert len(rows) == 1
    assert rows[0].staff_id == "staff-demo-1"


@pytest.mark.postgres
def test_postgres_round_trip_create_activity(postgres_url: str):
    store = PostgresStaffStore(build_engine(postgres_url))
    store.migrate()
    from sentinel_merchant_teams.domain.types import MerchantStaff, StaffActivity

    staff = MerchantStaff(
        staff_id="staff-pg-1",
        tenant_id="tenant-demo",
        merchant_ref="merchant-demo-1",
        display_name="Pg Staff",
        roles=("viewer",),
        active=True,
    )
    store.create(staff)
    store.append_activity(
        StaffActivity(
            event_id="event-pg-1",
            staff_id="staff-pg-1",
            at="2026-11-15T00:00:00Z",
            kind="STAFF_CREATED",
            subject_ref="merchant-demo-1",
            summary="Created staff Pg Staff",
        )
    )
    got = store.get(tenant_id="tenant-demo", staff_id="staff-pg-1")
    assert got is not None
    assert got.display_name == "Pg Staff"
    events = store.list_activity(staff_id="staff-pg-1")
    assert len(events) == 1
    assert events[0].kind == "STAFF_CREATED"
