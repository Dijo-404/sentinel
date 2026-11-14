"""Private disposable PostgreSQL for durable dispatcher checkpoints."""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import OperationalError

from sentinel_dispatcher.adapters.clock import FixedClock
from sentinel_dispatcher.adapters.memory_store import MemoryWorkerStore
from sentinel_dispatcher.adapters.postgres_store import PostgresWorkerStore, ensure_schema
from sentinel_dispatcher.application.worker import DispatchWorker
from sentinel_dispatcher.domain.types import Command
from tests.stubs.ledger import StubLedger
from tests.stubs.provider import StubProvider

IMAGE = "postgres:17-alpine@sha256:d3244e8ce3f165ee3c93d9c4a4b1d0fe48b3a89e2287b717fdcbbde92d405065"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "demo_command.json"
TENANT = "tenant-demo"
NOW = datetime(2026, 11, 13, 12, 0, 0, tzinfo=UTC)


def docker(*args: str) -> str:
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"Docker command failed: {result.stderr.strip()}")
    return result.stdout.strip()


@pytest.fixture(scope="session")
def demo_fixture() -> dict:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


@pytest.fixture
def demo_command(demo_fixture: dict) -> Command:
    return Command.from_mapping(demo_fixture["claim_one_response"]["commands"][0])


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(NOW)


@pytest.fixture
def memory_worker(demo_command: Command, clock: FixedClock):
    ledger = StubLedger([demo_command], tenant_id=TENANT)
    provider = StubProvider(mode="valid")
    store = MemoryWorkerStore()
    worker = DispatchWorker(
        tenant_id=TENANT,
        ledger=ledger,
        provider=provider,
        store=store,
        clock=clock,
    )
    return worker, ledger, provider, store


@pytest.fixture(scope="session")
def postgres():
    name = "sentinel-sn010-" + secrets.token_hex(6)
    database = "sentinel_demo_" + secrets.token_hex(6)
    password = secrets.token_urlsafe(24)
    admin = None
    with tempfile.NamedTemporaryFile(mode="w", prefix="sn010-env-") as env_file:
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
            with admin.begin() as connection:
                connection.execute(text("REVOKE ALL ON SCHEMA public FROM PUBLIC"))
                connection.execute(text(f'REVOKE ALL ON DATABASE "{database}" FROM PUBLIC'))
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
def pg_store(postgres):
    schema = "dispatcher_" + secrets.token_hex(4)
    ensure_schema(postgres, schema)
    return PostgresWorkerStore(postgres, schema=schema)


@pytest.fixture
def durable_worker(demo_command: Command, clock: FixedClock, pg_store: PostgresWorkerStore):
    ledger = StubLedger([demo_command], tenant_id=TENANT)
    provider = StubProvider(mode="valid")
    worker = DispatchWorker(
        tenant_id=TENANT,
        ledger=ledger,
        provider=provider,
        store=pg_store,
        clock=clock,
    )
    return worker, ledger, provider, pg_store
