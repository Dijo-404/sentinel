"""Postgres seed: one RunReport; HTTP serves DB rows."""

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

from sentinel_evaluation.adapters.storage_postgres import PostgresReportStore, build_engine
from sentinel_evaluation.application.errors import ConfigurationError
from sentinel_evaluation.composition.http_app import Settings, build_app
from sentinel_evaluation.domain.models import CONTRACT_VERSION
from sentinel_evaluation.seed import SEED_RUN_ID, seed_demo_report

IMAGE = "postgres:17-alpine@sha256:d3244e8ce3f165ee3c93d9c4a4b1d0fe48b3a89e2287b717fdcbbde92d405065"


def docker(*args: str) -> str:
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"Docker command failed: {result.stderr.strip()}")
    return result.stdout.strip()


@pytest.fixture(scope="module")
def postgres_url():
    name = "sentinel-eval-" + secrets.token_hex(6)
    database = "sentinel_eval_" + secrets.token_hex(6)
    password = "eval" + secrets.token_hex(12)
    engine = None
    with tempfile.NamedTemporaryFile(mode="w", prefix="eval-pg-env-") as env_file:
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


def test_seed_refuses_missing_database_url() -> None:
    with pytest.raises(ConfigurationError):
        seed_demo_report("")


@pytest.mark.postgres
def test_seed_report_served_from_postgres(postgres_url: str) -> None:
    report = seed_demo_report(postgres_url)
    assert report["status"] == "PASS"
    assert report["run_id"] == SEED_RUN_ID
    assert report["rows"] == 1

    store = PostgresReportStore(build_engine(postgres_url))
    loaded = store.get_report(SEED_RUN_ID)
    assert loaded is not None
    assert loaded["run_id"] == SEED_RUN_ID
    assert loaded["status"] == "PASS"
    assert loaded["contract_version"] == CONTRACT_VERSION

    again = seed_demo_report(postgres_url)
    assert again["run_id"] == SEED_RUN_ID
    assert len(store.list_reports()) == 1

    settings = Settings(
        mode="real-peers",
        tokens=TOKENS,
        database_url=postgres_url,
        contract_version=CONTRACT_VERSION,
    )
    client = TestClient(build_app(settings))
    headers = {"Authorization": "Bearer admin-token"}

    listed = client.get("/v1/reports", headers=headers)
    assert listed.status_code == 200
    body = listed.json()
    assert len(body["reports"]) == 1
    assert body["reports"][0]["run_id"] == SEED_RUN_ID

    one = client.get(f"/v1/reports/{SEED_RUN_ID}", headers=headers)
    assert one.status_code == 200
    assert one.json()["status"] == "PASS"
