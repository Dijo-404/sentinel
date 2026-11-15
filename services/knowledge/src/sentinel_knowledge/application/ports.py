"""Narrow ports for article persistence and text embedding."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from ..domain.types import Article, SearchHit


class ArticleStore(Protocol):
    def list_articles(self, tenant_id: str) -> list[Article]: ...

    def get_article(self, tenant_id: str, article_id: str) -> Article | None: ...

    def search_articles(self, tenant_id: str, query: str, limit: int) -> list[SearchHit]: ...

    def upsert(self, article: Article) -> None: ...


class Embedder(Protocol):
    """Dense text embedder. Vectors are L2-normalized so dot product == cosine."""

    model_name: str
    dimension: int

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...
