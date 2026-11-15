"""Postgres + pgvector path: seed, embed, semantic search, reindex, fail closed.

Uses ``KNOWLEDGE_TEST_DATABASE_URL`` (a pgvector-enabled database) when set; otherwise
starts a private ``pgvector/pgvector:pg17`` container. Skipped when neither is available.
Embeddings come from the test-only FakeEmbedder unless ``KNOWLEDGE_TEST_REAL_EMBEDDER=1``.
"""

from __future__ import annotations

import contextlib
import os
import secrets
import shutil
import subprocess
import tempfile
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import OperationalError
from tests.conftest import TOKENS
from tests.fakes import FakeEmbedder
from tests.test_semantic import CORPUS, DUPLICATE, OTHER_TENANT

from sentinel_knowledge.application.errors import ConfigurationError, PeerUnavailableError
from sentinel_knowledge.bootstrap import Settings, build_app, build_postgres_store
from sentinel_knowledge.seed import SEED_ARTICLE_ID, SEED_TENANT_ID, seed_demo_articles

PGVECTOR_IMAGE = (
    "pgvector/pgvector:pg17@sha256:b513c48566e4777cd3370451400000c78eda6a08131d68f4c31d4a76f27bd8fd"
)
PLAIN_IMAGE = (
    "postgres:17-alpine@sha256:d3244e8ce3f165ee3c93d9c4a4b1d0fe48b3a89e2287b717fdcbbde92d405065"
)


def docker(*args: str) -> str:
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise RuntimeError(f"Docker command failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True, timeout=30).returncode == 0


@contextlib.contextmanager
def private_postgres(image: str):
    if not _docker_available():
        pytest.skip("Docker unavailable and KNOWLEDGE_TEST_DATABASE_URL unset")
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
                image,
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


@pytest.fixture(scope="module")
def postgres_url():
    external = os.environ.get("KNOWLEDGE_TEST_DATABASE_URL")
    if external:
        yield external
        return
    with private_postgres(PGVECTOR_IMAGE) as url:
        yield url


@pytest.fixture(scope="module")
def embedder():
    if os.environ.get("KNOWLEDGE_TEST_REAL_EMBEDDER") == "1":
        from sentinel_knowledge.bootstrap import build_embedder

        return build_embedder(Settings.from_environ())
    return FakeEmbedder()


def _token_map() -> str:
    parts = []
    for token, principal in TOKENS.items():
        roles = ",".join(principal.roles)
        subjects = ",".join(principal.subject_refs)
        parts.append(f"{token}={principal.principal_id}|{principal.tenant_id}|{roles}|{subjects}")
    return ";".join(parts)


def _settings(url: str) -> Settings:
    return Settings(
        mode="real-peers",
        tokens=_token_map(),
        database_url=url,
        contract_version="sentinel.task-contracts.v1",
    )


HEADERS = {"Authorization": "Bearer operator-token"}


def test_seed_refuses_missing_database_url():
    with pytest.raises(ConfigurationError):
        seed_demo_articles("")


@pytest.mark.postgres
def test_seed_inserts_embedded_article_and_serves_from_postgres(postgres_url, embedder):
    report = seed_demo_articles(postgres_url, embedder)
    assert report["status"] == "PASS"
    assert report["tenant_id"] == SEED_TENANT_ID
    assert SEED_ARTICLE_ID in report["article_ids"]
    assert report["rows"] >= 1
    again = seed_demo_articles(postgres_url, embedder)
    assert again["article_ids"] == report["article_ids"]

    engine = create_engine(postgres_url)
    with engine.connect() as connection:
        model = connection.execute(
            text(
                "SELECT embedding_model FROM knowledge.articles "
                "WHERE article_id = :id AND embedding IS NOT NULL"
            ),
            {"id": SEED_ARTICLE_ID},
        ).scalar_one()
    engine.dispose()
    assert model == embedder.model_name

    client = TestClient(build_app(_settings(postgres_url), embedder=embedder))
    assert client.get("/v1/capabilities").json()["search"] == "semantic-hybrid"
    listed = client.get("/v1/articles", headers=HEADERS)
    assert SEED_ARTICLE_ID in [a["article_id"] for a in listed.json()["articles"]]
    detail = client.get(f"/v1/articles/{SEED_ARTICLE_ID}", headers=HEADERS)
    assert detail.status_code == 200 and detail.json()["body"]
    search = client.get("/v1/search", params={"q": "refund"}, headers=HEADERS)
    assert search.status_code == 200
    assert any(h["article_id"] == SEED_ARTICLE_ID for h in search.json()["hits"])


@pytest.mark.postgres
def test_pgvector_semantic_ranking_and_tenant_scope(postgres_url, embedder):
    store = build_postgres_store(_settings(postgres_url), embedder)
    for article in CORPUS:
        store.upsert(article)
    client = TestClient(build_app(_settings(postgres_url), store=store))

    response = client.get("/v1/search", params={"q": "charged twice", "limit": 3}, headers=HEADERS)
    assert response.status_code == 200
    hits = response.json()["hits"]
    assert hits[0]["article_id"] == DUPLICATE.article_id
    assert len(hits) <= 3
    assert hits == sorted(hits, key=lambda h: -h["score"])
    assert all(h["article_id"] != OTHER_TENANT.article_id for h in hits)

    other = client.get(
        "/v1/search",
        params={"q": "charged twice"},
        headers={"Authorization": "Bearer other-tenant-token"},
    )
    assert [h["article_id"] for h in other.json()["hits"]] == [OTHER_TENANT.article_id]


@pytest.mark.postgres
def test_reindex_backfills_and_dimension_change_fails_closed(postgres_url, embedder):
    store = build_postgres_store(_settings(postgres_url), embedder)
    store.upsert(DUPLICATE)
    engine = create_engine(postgres_url)
    with engine.begin() as connection:
        connection.execute(text("UPDATE knowledge.articles SET embedding = NULL"))
    assert store.reindex() >= 1
    assert store.reindex() == 0  # nothing stale left
    with engine.connect() as connection:
        missing = connection.execute(
            text("SELECT count(*) FROM knowledge.articles WHERE embedding IS NULL")
        ).scalar_one()
    engine.dispose()
    assert missing == 0

    class WiderEmbedder(FakeEmbedder):
        def __init__(self) -> None:
            super().__init__("test/wider")
            self.dimension = 48

    with pytest.raises(ConfigurationError):
        build_postgres_store(_settings(postgres_url), WiderEmbedder())


@pytest.mark.postgres
def test_missing_pgvector_extension_fails_closed():
    if os.environ.get("KNOWLEDGE_TEST_DATABASE_URL"):
        pytest.skip("needs a private plain-Postgres container")
    with private_postgres(PLAIN_IMAGE) as url:
        with pytest.raises(PeerUnavailableError):
            build_app(_settings(url), embedder=FakeEmbedder())
