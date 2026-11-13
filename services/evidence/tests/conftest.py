"""Shared fixtures: synthetic principals, fixed clock, optional private PostgreSQL."""

from __future__ import annotations

import os
import secrets
import subprocess
import tempfile
import time
from datetime import UTC, datetime

import pytest
from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import OperationalError

from sentinel_evidence.adapters.auth import TokenAuthenticator
from sentinel_evidence.adapters.clock import FixedClock
from sentinel_evidence.adapters.http_api import AppServices, create_app
from sentinel_evidence.adapters.provider_stub import CaseSelectingStub
from sentinel_evidence.adapters.storage_memory import MemoryEvidenceStore
from sentinel_evidence.application.collect import CollectEvidence, ListEvidence
from sentinel_evidence.domain.types import Principal

IMAGE = "postgres:17-alpine@sha256:d3244e8ce3f165ee3c93d9c4a4b1d0fe48b3a89e2287b717fdcbbde92d405065"

WORKFLOW = Principal(
    principal_id="svc-workflow",
    tenant_id="tenant-demo",
    roles=("workflow",),
    subject_refs=("subj-demo-1",),
    case_ids=("case-demo-42",),
)

TOKENS = {
    "tok-workflow": WORKFLOW,
    "tok-verifier": Principal(
        "svc-verifier",
        "tenant-demo",
        ("verifier",),
        ("subj-demo-1",),
        ("case-demo-42",),
    ),
    "workflow-token": WORKFLOW,
    "verifier-token": Principal(
        "svc-verifier",
        "tenant-demo",
        ("verifier",),
        ("subj-demo-1",),
        ("case-demo-42",),
    ),
    "operator-token": Principal(
        "op-1",
        "tenant-demo",
        ("operator",),
        ("subj-demo-1",),
        ("case-demo-42",),
    ),
    "customer-token": Principal(
        "cust-1",
        "tenant-demo",
        ("customer",),
        ("subj-demo-1",),
        ("case-demo-42",),
    ),
}


@pytest.fixture
def clock():
    return FixedClock(datetime(2026, 11, 13, 12, 30, tzinfo=UTC))


@pytest.fixture
def store():
    return MemoryEvidenceStore()


@pytest.fixture
def app(clock, store):
    services = AppServices(
        authenticator=TokenAuthenticator(TOKENS),
        collect=CollectEvidence(CaseSelectingStub(), store, clock),
        list_evidence=ListEvidence(store),
        mode="fixture",
    )
    return create_app(services)


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    return TestClient(app)


def docker(*args):
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"Docker command failed: {result.stderr.strip()}")
    return result.stdout.strip()


@pytest.fixture(scope="session")
def postgres():
    name = "sentinel-sn006-" + secrets.token_hex(6)
    database = "sentinel_evidence_" + secrets.token_hex(6)
    password = secrets.token_urlsafe(24)
    admin = None
    with tempfile.NamedTemporaryFile(mode="w", prefix="sn006-env-") as env_file:
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
