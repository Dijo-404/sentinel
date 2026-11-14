"""Sandbox seed: ≥1 knowledge article for tenant-demo."""

from __future__ import annotations

from typing import Any

from .adapters.storage_postgres import PostgresArticleStore, build_engine
from .application.errors import ConfigurationError
from .domain.types import Article

SEED_TENANT_ID = "tenant-demo"
SEED_ARTICLE_ID = "article-demo-refund-policy"
SEED_UPDATED_AT = "2026-11-14T10:00:00Z"

SEED_ARTICLE = Article(
    article_id=SEED_ARTICLE_ID,
    tenant_id=SEED_TENANT_ID,
    title="Sandbox refund policy",
    summary="Synthetic guidance for duplicate-charge refunds.",
    body=(
        "Synthetic sandbox article. Operators may cite this for tenant-demo "
        "refund investigations. No money authority."
    ),
    updated_at=SEED_UPDATED_AT,
)


def seed_demo_articles(database_url: str) -> dict[str, Any]:
    """Write synthetic knowledge rows. Requires KNOWLEDGE_DATABASE_URL."""
    if not database_url.strip():
        raise ConfigurationError("KNOWLEDGE_DATABASE_URL is required for seed")
    if SEED_ARTICLE.tenant_id != SEED_TENANT_ID:
        raise ConfigurationError(f"seed refuses tenant_id != {SEED_TENANT_ID}")

    store = PostgresArticleStore(build_engine(database_url))
    store.migrate()
    store.upsert(SEED_ARTICLE)
    return {
        "status": "PASS",
        "peer": "knowledge",
        "tenant_id": SEED_TENANT_ID,
        "article_ids": [SEED_ARTICLE_ID],
        "rows": 1,
        "evidence_label": "synthetic-sandbox",
    }
