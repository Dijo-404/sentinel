"""Disposable PostgreSQL + wired FastAPI app for SN-007."""

from __future__ import annotations

import os
import secrets
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import OperationalError

from sentinel_api.adapters.db.repository import SqlCaseRepository
from sentinel_api.adapters.db.schema import metadata
from sentinel_api.adapters.http.app import create_app
from sentinel_api.adapters.http.auth import CompositePrincipalResolver, TokenMap
from sentinel_api.adapters.identity.fixture import FixtureIdentityPrincipalAdapter
from sentinel_api.adapters.peers.fixture_clients import (
    FixtureEvidenceClient,
    FixtureLedgerClient,
    FixtureVerifierClient,
    FixtureWorkflowClient,
)
from sentinel_api.application.service import CaseService
from sentinel_api.bootstrap import SecureIds, SystemClock

IMAGE = "postgres:17-alpine@sha256:d3244e8ce3f165ee3c93d9c4a4b1d0fe48b3a89e2287b717fdcbbde92d405065"
TOKENS_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "auth_tokens.json"
IDENTITY_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "identity_sessions.json"


def docker(*args: str) -> str:
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"Docker command failed: {result.stderr.strip()}")
    return result.stdout.strip()


@pytest.fixture(scope="session")
def postgres():
    name = "sentinel-sn007-" + secrets.token_hex(6)
    database = "sentinel_api_" + secrets.token_hex(6)
    password = secrets.token_hex(24)
    admin = None
    with tempfile.NamedTemporaryFile(mode="w", prefix="sn007-env-") as env_file:
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
            admin = create_engine(url, hide_parameters=True)
            deadline = time.monotonic() + 45
            while True:
                try:
                    with admin.connect() as connection:
                        connection.execute(text("SELECT 1"))
                    break
                except OperationalError:
                    if time.monotonic() >= deadline:
                        raise RuntimeError("Private PostgreSQL did not become ready") from None
                    time.sleep(0.2)
            yield admin
        finally:
            if admin is not None:
                admin.dispose()
            subprocess.run(
                ["docker", "rm", "--force", name],
                capture_output=True,
                timeout=30,
                check=False,
            )


@pytest.fixture
def engine(postgres):
    engine = create_engine(postgres.url, hide_parameters=True)
    metadata.drop_all(engine)
    metadata.create_all(engine)
    yield engine
    metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def peers():
    return {
        "workflow": FixtureWorkflowClient(),
        "evidence": FixtureEvidenceClient(),
        "ledger": FixtureLedgerClient(),
        "verifier": FixtureVerifierClient(),
    }


@pytest.fixture
def app(engine, peers):
    repo = SqlCaseRepository(engine)
    service = CaseService(
        repo=repo,
        clock=SystemClock(),
        ids=SecureIds(),
        workflow=peers["workflow"],
        evidence=peers["evidence"],
        ledger=peers["ledger"],
        verifier=peers["verifier"],
        service_authorization="Bearer token-case-api-service",
    )
    tokens = TokenMap.from_path(TOKENS_PATH)
    identity = FixtureIdentityPrincipalAdapter.from_path(IDENTITY_PATH)
    resolver = CompositePrincipalResolver(identity=identity, tokens=tokens)

    def readiness():
        repo.ping()
        return {"ready": True, "mode": "fixture", "label": "fixture-local"}

    application = create_app(service=service, tokens=resolver, mode="fixture", readiness=readiness)
    application.state.engine = engine
    application.state.repo = repo
    application.state.peers = peers
    application.state.service = service
    return application


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def fixed_now() -> datetime:
    return datetime(2026, 11, 13, 12, 0, 0, tzinfo=UTC)
