"""Knowledge use cases: list, get, search. No money authority."""

from __future__ import annotations

from ..domain.types import (
    DEFAULT_SEARCH_LIMIT,
    MAX_SEARCH_LIMIT,
    Article,
    Principal,
    SearchHit,
)
from .errors import NotFoundError, UnauthorizedError, ValidationError
from .ports import ArticleStore


class KnowledgeService:
    def __init__(self, store: ArticleStore):
        self._store = store

    def list_articles(self, principal: Principal) -> list[Article]:
        self._require_reader(principal)
        return self._store.list_articles(principal.tenant_id)

    def get_article(self, principal: Principal, article_id: str) -> Article:
        self._require_reader(principal)
        article = self._store.get_article(principal.tenant_id, article_id)
        if article is None:
            raise NotFoundError("Article not found")
        return article

    def search(
        self, principal: Principal, query: str, limit: int = DEFAULT_SEARCH_LIMIT
    ) -> list[SearchHit]:
        self._require_reader(principal)
        q = query.strip()
        if not q:
            raise ValidationError("q is required")
        if not 1 <= limit <= MAX_SEARCH_LIMIT:
            raise ValidationError(f"limit must be between 1 and {MAX_SEARCH_LIMIT}")
        return self._store.search_articles(principal.tenant_id, q, limit)

    @staticmethod
    def _require_reader(principal: Principal) -> None:
        if not principal.allows_knowledge():
            raise UnauthorizedError("Knowledge access denied")
