"""Postgres KNOWLEDGE_DATABASE_URL path: seed + serve articles from DB."""

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

from sentinel_knowledge.bootstrap import Settings, build_app
from sentinel_knowledge.seed import SEED_ARTICLE_ID, SEED_TENANT_ID, seed_demo_articles

IMAGE = "postgres:17-alpine@sha256:d3244e8ce3f165ee3c93d9c4a4b1d0fe48b3a89e2287b717fdcbbde92d405065"


def docker(*args: str) -> str:
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"Docker command failed: {result.stderr.strip()}")
    return result.stdout.strip()


@pytest.fixture(scope="module")
def postgres_url():
    name = "sentinel-knowledge-" + secrets.token_hex(6)
    database = "sentinel_knowledge_" + secrets.token_hex(6)
    password = "know" + secrets.token_hex(12)
    engine = None
    with tempfile.NamedTemporaryFile(mode="w", prefix="knowledge-pg-env-") as env_file:
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
        subjects = ",".join(principal.subject_refs)
        parts.append(f"{token}={principal.principal_id}|{principal.tenant_id}|{roles}|{subjects}")
    return ";".join(parts)


def test_seed_refuses_missing_database_url():
    from sentinel_knowledge.application.errors import ConfigurationError

    with pytest.raises(ConfigurationError):
        seed_demo_articles("")


@pytest.mark.postgres
def test_seed_inserts_article_and_lists_from_postgres(postgres_url: str):
    report = seed_demo_articles(postgres_url)
    assert report["status"] == "PASS"
    assert report["tenant_id"] == SEED_TENANT_ID
    assert SEED_ARTICLE_ID in report["article_ids"]
    assert report["rows"] >= 1

    again = seed_demo_articles(postgres_url)
    assert again["article_ids"] == report["article_ids"]

    settings = Settings(
        mode="fixture",
        tokens=_token_map(),
        database_url=postgres_url,
        contract_version="sentinel.task-contracts.v1",
    )
    client = TestClient(build_app(settings))
    headers = {"Authorization": "Bearer operator-token"}

    listed = client.get("/v1/articles", headers=headers)
    assert listed.status_code == 200
    ids = [a["article_id"] for a in listed.json()["articles"]]
    assert SEED_ARTICLE_ID in ids

    detail = client.get(f"/v1/articles/{SEED_ARTICLE_ID}", headers=headers)
    assert detail.status_code == 200
    assert "body" in detail.json()
    assert detail.json()["body"]

    search = client.get("/v1/search", params={"q": "refund"}, headers=headers)
    assert search.status_code == 200
    assert any(h["article_id"] == SEED_ARTICLE_ID for h in search.json()["hits"])
