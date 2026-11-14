"""Shared fixtures: synthetic principals and memory-backed app."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sentinel_knowledge.adapters.auth import TokenAuthenticator
from sentinel_knowledge.adapters.http import AppServices, create_app
from sentinel_knowledge.adapters.storage_memory import MemoryArticleStore
from sentinel_knowledge.application.service import KnowledgeService
from sentinel_knowledge.domain.types import Article, Principal

OPERATOR = Principal(
    principal_id="op-1",
    tenant_id="tenant-demo",
    roles=("operator",),
    subject_refs=("subj-demo-1",),
)

TOKENS = {
    "operator-token": OPERATOR,
    "supervisor-token": Principal(
        "sup-1",
        "tenant-demo",
        ("supervisor",),
        ("subj-demo-1",),
    ),
    "other-tenant-token": Principal(
        "op-2",
        "tenant-other",
        ("operator",),
        ("subj-other",),
    ),
    "customer-token": Principal(
        "cust-1",
        "tenant-demo",
        ("customer",),
        ("subj-demo-1",),
    ),
}

SEED_ARTICLE = Article(
    article_id="article-demo-refund-policy",
    tenant_id="tenant-demo",
    title="Sandbox refund policy",
    summary="Synthetic guidance for duplicate-charge refunds.",
    body=(
        "Synthetic sandbox article. Operators may cite this for tenant-demo "
        "refund investigations. No money authority."
    ),
    updated_at="2026-11-14T10:00:00Z",
)


@pytest.fixture
def store() -> MemoryArticleStore:
    memory = MemoryArticleStore()
    memory.upsert(SEED_ARTICLE)
    return memory


@pytest.fixture
def app(store: MemoryArticleStore):
    return create_app(
        AppServices(
            authenticator=TokenAuthenticator(TOKENS),
            knowledge=KnowledgeService(store=store),
            mode="fixture",
        )
    )


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


def auth(token: str = "operator-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
