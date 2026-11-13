"""Private disposable PostgreSQL and fixture app wiring."""

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
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import OperationalError
from tests.stubs.case_api import StubCaseApi
from tests.stubs.evidence import StubEvidence
from tests.stubs.ledger import StubLedger
from tests.stubs.provider import StubProvider

from sentinel_verifier.adapters.auth_tokens import TokenPrincipalMap, demo_principals
from sentinel_verifier.adapters.clock import FixedClock
from sentinel_verifier.adapters.ids import SequenceIdGenerator
from sentinel_verifier.adapters.memory_store import MemoryVerifierStore
from sentinel_verifier.adapters.postgres_store import PostgresVerifierStore, ensure_schema
from sentinel_verifier.bootstrap import build_app
from sentinel_verifier.domain.signature import signature_hex
from sentinel_verifier.domain.types import Credit, Refund

IMAGE = "postgres:17-alpine@sha256:d3244e8ce3f165ee3c93d9c4a4b1d0fe48b3a89e2287b717fdcbbde92d405065"
ROOT = Path(__file__).resolve().parents[1]
HMAC_KEY = "demo-simulator-hmac-key"
TENANT = "tenant-demo-1"
MERCHANT = "merchant-demo-1"
NOW = datetime(2026, 11, 13, 12, 0, 0, tzinfo=UTC)
PROVIDER_REF = "refund-demo-1"
ACTION_ID = "action-demo-1"
CASE_ID = "case-demo-42"


def docker(*args: str) -> str:
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"Docker command failed: {result.stderr.strip()}")
    return result.stdout.strip()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def signed_webhook(body: dict, *, key: str = HMAC_KEY) -> tuple[bytes, str]:
    raw = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return raw, signature_hex(raw, key=key)


@pytest.fixture(scope="session")
def postgres_url():
    name = "sentinel-sn011-" + secrets.token_hex(6)
    database = "sentinel_verifier_" + secrets.token_hex(6)
    password = secrets.token_urlsafe(24)
    engine = None
    with tempfile.NamedTemporaryFile(mode="w", prefix="sn011-env-") as env_file:
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
            yield url
        finally:
            if engine is not None:
                engine.dispose()
            subprocess.run(
                ["docker", "rm", "--force", name],
                capture_output=True,
                timeout=30,
                check=False,
            )


@pytest.fixture
def engine(postgres_url):
    eng = create_engine(postgres_url, hide_parameters=True, pool_size=8, max_overflow=4)
    schema = "verifier_" + secrets.token_hex(4)
    ensure_schema(eng, schema)
    yield eng, schema
    eng.dispose()


@pytest.fixture
def clock():
    return FixedClock(NOW)


@pytest.fixture
def peers():
    provider = StubProvider()
    ledger = StubLedger()
    evidence = StubEvidence()
    case_api = StubCaseApi()
    ledger.seed_action(action_id=ACTION_ID, provider_ref=PROVIDER_REF, status="PENDING")
    provider.seed_refund(
        Refund(
            action_id=ACTION_ID,
            provider_ref=PROVIDER_REF,
            transaction_ref="TXN-B",
            amount_minor=150000,
            currency="INR",
            status="PENDING",
        )
    )
    evidence.seed(CASE_ID)
    case_api.seed(CASE_ID)
    return provider, ledger, evidence, case_api


@pytest.fixture
def memory_client(clock, peers):
    provider, ledger, evidence, case_api = peers
    store = MemoryVerifierStore()
    app = build_app(
        store=store,
        provider=provider,
        ledger=ledger,
        evidence=evidence,
        case_api=case_api,
        auth=TokenPrincipalMap(demo_principals(TENANT)),
        clock=clock,
        ids=SequenceIdGenerator(),
        mode="fixture",
        webhook_hmac_key=HMAC_KEY,
        merchant_map={MERCHANT: TENANT},
        enforce_event_age=False,
    )
    client = TestClient(app)
    client.store = store
    client.provider = provider
    client.ledger = ledger
    client.evidence = evidence
    client.case_api = case_api
    client.clock = clock
    return client


@pytest.fixture
def pg_client(engine, clock, peers):
    eng, schema = engine
    provider, ledger, evidence, case_api = peers
    store = PostgresVerifierStore(eng, schema=schema)
    app = build_app(
        store=store,
        provider=provider,
        ledger=ledger,
        evidence=evidence,
        case_api=case_api,
        auth=TokenPrincipalMap(demo_principals(TENANT)),
        clock=clock,
        ids=SequenceIdGenerator(),
        mode="fixture",
        webhook_hmac_key=HMAC_KEY,
        merchant_map={MERCHANT: TENANT},
        enforce_event_age=False,
    )
    client = TestClient(app)
    client.store = store
    client.provider = provider
    client.ledger = ledger
    client.evidence = evidence
    client.case_api = case_api
    client.clock = clock
    client.engine = eng
    client.schema = schema
    return client


@pytest.fixture
def tokens():
    return {
        "workflow": "token-workflow-demo",
        "verifier": "token-verifier-demo",
        "case_api": "token-case-api-demo",
        "operator": "token-operator-demo",
    }


@pytest.fixture
def verification_request():
    return {
        "case_id": CASE_ID,
        "case_revision": 1,
        "action_id": ACTION_ID,
        "provider_ref": PROVIDER_REF,
    }


@pytest.fixture
def webhook_body():
    return {
        "event_id": "evt-demo-1",
        "tenant_id": TENANT,
        "merchant_ref": MERCHANT,
        "provider_ref": PROVIDER_REF,
        "type": "REFUND_STATUS",
        "occurred_at": "2026-11-13T11:59:00Z",
    }


@pytest.fixture
def credit_confirmed(peers):
    provider, _ledger, _evidence, _case = peers
    provider.seed_refund(
        Refund(
            action_id=ACTION_ID,
            provider_ref=PROVIDER_REF,
            transaction_ref="TXN-B",
            amount_minor=150000,
            currency="INR",
            status="PROVIDER_CONFIRMED",
        )
    )
    provider.seed_credit(
        Credit(provider_ref=PROVIDER_REF, confirmed=True, observed_at="2026-11-13T12:00:00Z")
    )
