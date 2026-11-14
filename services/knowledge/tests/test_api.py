"""HTTP API: articles, search, auth, capabilities."""

from __future__ import annotations

from fastapi.testclient import TestClient
from tests.conftest import SEED_ARTICLE, auth


def test_health_ready_capabilities(client: TestClient):
    assert client.get("/healthz").json() == {"status": "ok"}
    ready = client.get("/readyz").json()
    assert ready["status"] == "ready"
    assert ready["mode"] == "fixture"
    caps = client.get("/v1/capabilities").json()
    assert caps["contract_version"] == "sentinel.task-contracts.v1"
    assert caps["component"] == "knowledge"
    assert caps["mode"] == "fixture"
    assert caps["financial_authority"] is False


def test_list_articles(client: TestClient):
    response = client.get("/v1/articles", headers=auth())
    assert response.status_code == 200
    body = response.json()
    assert "articles" in body
    assert len(body["articles"]) >= 1
    article = next(a for a in body["articles"] if a["article_id"] == SEED_ARTICLE.article_id)
    assert article == {
        "article_id": SEED_ARTICLE.article_id,
        "title": SEED_ARTICLE.title,
        "summary": SEED_ARTICLE.summary,
        "updated_at": SEED_ARTICLE.updated_at,
    }
    assert "body" not in article


def test_get_article_body(client: TestClient):
    response = client.get(
        f"/v1/articles/{SEED_ARTICLE.article_id}",
        headers=auth(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["article_id"] == SEED_ARTICLE.article_id
    assert body["title"] == SEED_ARTICLE.title
    assert body["summary"] == SEED_ARTICLE.summary
    assert body["body"] == SEED_ARTICLE.body
    assert body["updated_at"] == SEED_ARTICLE.updated_at


def test_get_article_missing(client: TestClient):
    response = client.get("/v1/articles/missing", headers=auth())
    assert response.status_code == 404
    assert response.json()["code"] == "ARTICLE_NOT_FOUND"


def test_search_by_title(client: TestClient):
    response = client.get("/v1/search", params={"q": "refund"}, headers=auth())
    assert response.status_code == 200
    hits = response.json()["hits"]
    assert any(h["article_id"] == SEED_ARTICLE.article_id for h in hits)
    hit = next(h for h in hits if h["article_id"] == SEED_ARTICLE.article_id)
    assert hit["title"] == SEED_ARTICLE.title
    assert hit["summary"] == SEED_ARTICLE.summary


def test_search_requires_q(client: TestClient):
    response = client.get("/v1/search", headers=auth())
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_INPUT"


def test_unauthorized_missing_token(client: TestClient):
    response = client.get("/v1/articles")
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_customer_role_denied(client: TestClient):
    response = client.get("/v1/articles", headers=auth("customer-token"))
    assert response.status_code == 403


def test_other_tenant_sees_empty_list(client: TestClient):
    response = client.get("/v1/articles", headers=auth("other-tenant-token"))
    assert response.status_code == 200
    assert response.json()["articles"] == []


def test_other_tenant_cannot_fetch_article(client: TestClient):
    response = client.get(
        f"/v1/articles/{SEED_ARTICLE.article_id}",
        headers=auth("other-tenant-token"),
    )
    assert response.status_code == 404
