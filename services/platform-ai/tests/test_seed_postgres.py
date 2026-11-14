"""Postgres seed: one config row + one run; APIs serve DB metadata."""

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
from tests.conftest import MONEY_KEYS, TOKENS

from sentinel_platform_ai.adapters.storage_postgres import PostgresPlatformAiStore, build_engine
from sentinel_platform_ai.bootstrap import Settings, build_app
from sentinel_platform_ai.seed import (
    SEED_MODEL_ID,
    SEED_RUN_ID,
    SEED_TENANT_ID,
    seed_demo_platform_ai,
)

IMAGE = "postgres:17-alpine@sha256:d3244e8ce3f165ee3c93d9c4a4b1d0fe48b3a89e2287b717fdcbbde92d405065"


def docker(*args: str) -> str:
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"Docker command failed: {result.stderr.strip()}")
    return result.stdout.strip()


@pytest.fixture(scope="module")
def postgres_url():
    name = "sentinel-pai-" + secrets.token_hex(6)
    database = "sentinel_pai_" + secrets.token_hex(6)
    password = "pai" + secrets.token_hex(12)
    engine = None
    with tempfile.NamedTemporaryFile(mode="w", prefix="pai-pg-env-") as env_file:
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


def _assert_no_money_fields(payload: object) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            assert key not in MONEY_KEYS, f"money field leaked: {key}"
            _assert_no_money_fields(value)
    elif isinstance(payload, list):
        for item in payload:
            _assert_no_money_fields(item)


def test_seed_refuses_missing_database_url():
    from sentinel_platform_ai.application.errors import ConfigurationError

    with pytest.raises(ConfigurationError):
        seed_demo_platform_ai("")


@pytest.mark.postgres
def test_seed_config_and_run_served_from_postgres(postgres_url: str):
    report = seed_demo_platform_ai(postgres_url)
    assert report["status"] == "PASS"
    assert report["tenant_id"] == SEED_TENANT_ID
    assert report["model_id"] == SEED_MODEL_ID
    assert report["run_id"] == SEED_RUN_ID
    assert report["rows"] == 2

    store = PostgresPlatformAiStore(build_engine(postgres_url))
    config = store.get_config(SEED_TENANT_ID)
    assert config is not None
    assert config.kill_switch is False
    assert config.models[0].model_id == SEED_MODEL_ID
    runs = store.list_runs(SEED_TENANT_ID)
    assert len(runs) == 1
    assert runs[0].run_id == SEED_RUN_ID

    again = seed_demo_platform_ai(postgres_url)
    assert again["run_id"] == SEED_RUN_ID
    assert len(store.list_runs(SEED_TENANT_ID)) == 1

    settings = Settings(
        mode="real-peers",
        tokens=TOKENS,
        database_url=postgres_url,
        contract_version="sentinel.task-contracts.v1",
    )
    client = TestClient(build_app(settings))
    headers = {"Authorization": "Bearer admin-token"}

    config_resp = client.get("/v1/config", headers=headers)
    assert config_resp.status_code == 200
    config_body = config_resp.json()
    assert config_body["models"][0]["model_id"] == SEED_MODEL_ID
    assert config_body["kill_switch"] is False
    _assert_no_money_fields(config_body)

    runs_resp = client.get("/v1/runs", headers=headers)
    assert runs_resp.status_code == 200
    runs_body = runs_resp.json()
    assert runs_body["runs"][0]["run_id"] == SEED_RUN_ID
    assert set(runs_body["runs"][0]) == {"run_id", "model_id", "status", "started_at"}
    _assert_no_money_fields(runs_body)
