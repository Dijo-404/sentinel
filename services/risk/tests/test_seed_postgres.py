"""Postgres RISK_DATABASE_URL path: seed case-demo-42 and serve list GETs from DB."""

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

from sentinel_risk.adapters.storage_postgres import PostgresRiskStore, build_engine
from sentinel_risk.bootstrap import Settings, build_app
from sentinel_risk.seed import (
    SEED_CASE_ID,
    SEED_FINDING_ID,
    SEED_INVESTIGATION_ID,
    SEED_RESTRICTION_ID,
    SEED_TENANT_ID,
    seed_demo_case,
)
from tests.conftest import TOKENS

IMAGE = "postgres:17-alpine@sha256:d3244e8ce3f165ee3c93d9c4a4b1d0fe48b3a89e2287b717fdcbbde92d405065"


def docker(*args: str) -> str:
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"Docker command failed: {result.stderr.strip()}")
    return result.stdout.strip()


@pytest.fixture(scope="module")
def postgres_url():
    name = "sentinel-risk-" + secrets.token_hex(6)
    database = "sentinel_risk_" + secrets.token_hex(6)
    # Alphanumeric only so URL round-trip never mangles auth.
    password = "risk" + secrets.token_hex(12)
    engine = None
    with tempfile.NamedTemporaryFile(mode="w", prefix="risk-pg-env-") as env_file:
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
    # Mirror .env.example risk-officer for case-demo-42 / FRAUD.
    parts = []
    for token, principal in TOKENS.items():
        cases = ",".join(principal.case_ids)
        queues = ",".join(principal.queue_refs) if principal.queue_refs else ""
        roles = ",".join(principal.roles)
        subjects = ",".join(principal.subject_refs)
        parts.append(
            f"{token}={principal.principal_id}|{principal.tenant_id}|{roles}|{subjects}|{cases}|{queues}"
        )
    return ";".join(parts)


def test_seed_refuses_missing_database_url():
    from sentinel_risk.application.errors import ConfigurationError

    with pytest.raises(ConfigurationError):
        seed_demo_case("")


def test_seed_inserts_case_demo_42_and_lists_from_postgres(postgres_url: str):
    report = seed_demo_case(postgres_url)
    assert report["status"] == "PASS"
    assert report["case_id"] == SEED_CASE_ID
    assert report["investigation_id"] == SEED_INVESTIGATION_ID
    assert report["restriction_id"] == SEED_RESTRICTION_ID
    assert SEED_FINDING_ID in report["finding_ids"]

    store = PostgresRiskStore(build_engine(postgres_url))
    investigation = store.get_investigation(SEED_INVESTIGATION_ID)
    assert investigation is not None
    assert investigation.tenant_id == SEED_TENANT_ID
    assert investigation.case_id == SEED_CASE_ID
    restriction = store.get_restriction(SEED_RESTRICTION_ID)
    assert restriction is not None
    assert restriction.blocks_financial_actions is True
    assert restriction.transaction_ref == "TXN-B"
    findings = store.list_findings(SEED_INVESTIGATION_ID)
    assert any(f.finding_id == SEED_FINDING_ID for f in findings)

    # Idempotent re-seed.
    again = seed_demo_case(postgres_url)
    assert again["investigation_id"] == SEED_INVESTIGATION_ID

    settings = Settings(
        mode="fixture",
        tokens=_token_map(),
        case_api_base_url="",
        case_api_token="",
        workflow_base_url="",
        workflow_token="",
        database_url=postgres_url,
        contract_version="sentinel.task-contracts.v1",
    )
    client = TestClient(build_app(settings))
    headers = {"Authorization": "Bearer risk-token"}

    queue = client.get("/v1/risk/investigations", headers=headers)
    assert queue.status_code == 200
    inv_ids = [i["investigation_id"] for i in queue.json()["investigations"]]
    assert SEED_INVESTIGATION_ID in inv_ids

    holds = client.get(
        "/v1/risk/restrictions",
        headers=headers,
        params={"blocks_financial_actions": "true"},
    )
    assert holds.status_code == 200
    assert any(r["restriction_id"] == SEED_RESTRICTION_ID for r in holds.json()["restrictions"])

    txns = client.get(
        "/v1/risk/restrictions",
        headers=headers,
        params={"has_transaction_ref": "true"},
    )
    assert txns.status_code == 200
    assert any(r["transaction_ref"] == "TXN-B" for r in txns.json()["restrictions"])

    audit = client.get("/v1/risk/findings", headers=headers)
    assert audit.status_code == 200
    assert any(f["finding_id"] == SEED_FINDING_ID for f in audit.json()["findings"])

    analytics = client.get("/v1/risk/dashboard", headers=headers)
    reports = client.get("/v1/risk/reports", headers=headers)
    assert analytics.status_code == 200
    assert reports.status_code == 200
    assert analytics.json()["open_investigations"] >= 1
    assert reports.json()["active_restrictions"] >= 1
