"""Semantic search: ranking, tenant scope, wire shape and fail-closed composition."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from tests.conftest import TOKENS, auth
from tests.fakes import FakeEmbedder

from sentinel_knowledge.adapters.auth import TokenAuthenticator
from sentinel_knowledge.adapters.http import AppServices, create_app
from sentinel_knowledge.adapters.storage_memory import MemoryArticleStore
from sentinel_knowledge.application.errors import PeerUnavailableError
from sentinel_knowledge.application.service import KnowledgeService
from sentinel_knowledge.bootstrap import Settings, build_app
from sentinel_knowledge.domain.types import Article

TS = "2026-11-14T10:00:00Z"
DUPLICATE = Article(
    "article-duplicate-payment",
    "tenant-demo",
    "Duplicate payment refunds",
    "When a customer is billed two times for one order, reverse the extra debit.",
    "Verify both debits on the original route before proposing a refund.",
    TS,
)
SHIPPING = Article(
    "article-shipping",
    "tenant-demo",
    "Shipping delays",
    "Courier delivery is delayed during festivals.",
    "Share the parcel tracking link with the customer.",
    TS,
)
ACCESS = Article(
    "article-access",
    "tenant-demo",
    "Password reset",
    "Help a merchant reset their dashboard login.",
    "Never ask for the current password.",
    TS,
)
OTHER_TENANT = Article(
    "article-other-duplicate",
    "tenant-other",
    "Duplicate payment (other tenant)",
    "Charged twice guidance owned by another tenant.",
    "Must never leak across tenants.",
    TS,
)
CORPUS = (DUPLICATE, SHIPPING, ACCESS, OTHER_TENANT)


def _store(embedder=None) -> MemoryArticleStore:
    store = MemoryArticleStore(embedder)
    for article in CORPUS:
        store.upsert(article)
    return store


@pytest.fixture
def semantic_client() -> TestClient:
    services = AppServices(
        authenticator=TokenAuthenticator(TOKENS),
        knowledge=KnowledgeService(store=_store(FakeEmbedder())),
        mode="fixture",
        search="semantic-hybrid",
    )
    return TestClient(create_app(services))


def test_semantic_match_beats_substring():
    query = "charged twice"
    assert _store().search_articles("tenant-demo", query, 10) == []  # old substring path
    hits = _store(FakeEmbedder()).search_articles("tenant-demo", query, 10)
    assert hits[0].article.article_id == DUPLICATE.article_id
    assert hits[0].score > hits[1].score


def test_keyword_bonus_lifts_exact_phrase():
    hits = _store(FakeEmbedder()).search_articles("tenant-demo", "dashboard login", 10)
    assert hits[0].article.article_id == ACCESS.article_id


def test_search_is_tenant_scoped():
    store = _store(FakeEmbedder())
    demo_ids = {h.article.article_id for h in store.search_articles("tenant-demo", "x", 50)}
    other_ids = {h.article.article_id for h in store.search_articles("tenant-other", "x", 50)}
    assert OTHER_TENANT.article_id not in demo_ids
    assert other_ids == {OTHER_TENANT.article_id}


def test_http_hits_keep_summary_shape_and_add_score(semantic_client: TestClient):
    response = semantic_client.get("/v1/search", params={"q": "charged twice"}, headers=auth())
    assert response.status_code == 200
    hits = response.json()["hits"]
    assert hits[0]["article_id"] == DUPLICATE.article_id
    assert set(hits[0]) == {"article_id", "title", "summary", "updated_at", "score"}
    assert all(h["article_id"] != OTHER_TENANT.article_id for h in hits)


def test_http_limit(semantic_client: TestClient):
    response = semantic_client.get("/v1/search", params={"q": "refund", "limit": 1}, headers=auth())
    assert response.status_code == 200
    assert len(response.json()["hits"]) == 1
    for bad in ("0", "51", "x"):
        response = semantic_client.get(
            "/v1/search", params={"q": "refund", "limit": bad}, headers=auth()
        )
        assert response.status_code == 422, bad
        assert response.json()["code"] == "INVALID_INPUT"


def test_http_search_still_requires_reader_role(semantic_client: TestClient):
    response = semantic_client.get(
        "/v1/search", params={"q": "refund"}, headers=auth("customer-token")
    )
    assert response.status_code == 403


def test_capabilities_label_search_mode(semantic_client: TestClient, client: TestClient):
    assert semantic_client.get("/v1/capabilities").json()["search"] == "semantic-hybrid"
    assert client.get("/v1/capabilities").json()["search"] == "substring"


def test_unknown_embedding_model_fails_closed():
    settings = Settings(
        mode="real-peers",
        tokens="",
        database_url="postgresql+psycopg://u:p@127.0.0.1:1/none",
        contract_version="sentinel.task-contracts.v1",
        embedding_model="nonexistent/not-a-model",
    )
    with pytest.raises(PeerUnavailableError):
        build_app(settings)


def test_real_peers_without_database_fails_closed():
    settings = Settings(
        mode="real-peers",
        tokens="",
        database_url="",
        contract_version="sentinel.task-contracts.v1",
    )
    with pytest.raises(PeerUnavailableError):
        build_app(settings)


@pytest.mark.real_embedder
@pytest.mark.skipif(
    os.environ.get("KNOWLEDGE_TEST_REAL_EMBEDDER") != "1",
    reason="set KNOWLEDGE_TEST_REAL_EMBEDDER=1 to download and run the real ONNX model",
)
@pytest.mark.parametrize(
    "query",
    [
        "charged twice",
        "मुझसे दो बार पैसे कट गए",  # Hindi: money was deducted from me twice
        "என்னிடம் இரண்டு முறை பணம் எடுக்கப்பட்டது",  # Tamil: money was taken twice
    ],
)
def test_real_model_ranks_duplicate_payment_first(query: str):
    from sentinel_knowledge.bootstrap import build_embedder

    embedder = build_embedder(Settings.from_environ())
    hits = _store(embedder).search_articles("tenant-demo", query, 3)
    assert hits[0].article.article_id == DUPLICATE.article_id
