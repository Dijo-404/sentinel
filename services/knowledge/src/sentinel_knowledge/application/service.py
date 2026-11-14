"""Knowledge use cases: list, get, search. No money authority."""

from __future__ import annotations

from ..domain.types import Article, Principal
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

    def search(self, principal: Principal, query: str) -> list[Article]:
        self._require_reader(principal)
        q = query.strip()
        if not q:
            raise ValidationError("q is required")
        return self._store.search_articles(principal.tenant_id, q)

    @staticmethod
    def _require_reader(principal: Principal) -> None:
        if not principal.allows_knowledge():
            raise UnauthorizedError("Knowledge access denied")
