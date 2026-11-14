"""Narrow ports for article persistence."""

from __future__ import annotations

from typing import Protocol

from ..domain.types import Article


class ArticleStore(Protocol):
    def list_articles(self, tenant_id: str) -> list[Article]: ...

    def get_article(self, tenant_id: str, article_id: str) -> Article | None: ...

    def search_articles(self, tenant_id: str, query: str) -> list[Article]: ...

    def upsert(self, article: Article) -> None: ...
