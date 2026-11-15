"""In-process article store for fixture/tests.

Without an embedder it keeps the fixture substring search. With an injected embedder
it ranks with the same hybrid rule as the Postgres store (cosine + keyword bonus).
"""

from __future__ import annotations

from ..application.ports import Embedder
from ..domain.types import KEYWORD_BONUS, Article, SearchHit


class MemoryArticleStore:
    def __init__(self, embedder: Embedder | None = None) -> None:
        self._by_id: dict[tuple[str, str], Article] = {}
        self._vectors: dict[tuple[str, str], list[float]] = {}
        self._embedder = embedder
        self.search_mode = "substring" if embedder is None else "semantic-hybrid"

    def upsert(self, article: Article) -> None:
        key = (article.tenant_id, article.article_id)
        if self._embedder is not None:
            self._vectors[key] = self._embedder.embed_passages([article.passage_text()])[0]
        self._by_id[key] = article

    def list_articles(self, tenant_id: str) -> list[Article]:
        rows = [a for (tid, _), a in self._by_id.items() if tid == tenant_id]
        return sorted(rows, key=lambda a: a.updated_at, reverse=True)

    def get_article(self, tenant_id: str, article_id: str) -> Article | None:
        return self._by_id.get((tenant_id, article_id))

    def search_articles(self, tenant_id: str, query: str, limit: int) -> list[SearchHit]:
        needle = query.casefold()
        articles = self.list_articles(tenant_id)
        if self._embedder is None:
            return [SearchHit(a) for a in articles if needle in a.passage_text().casefold()][:limit]
        q = self._embedder.embed_query(query)
        hits = []
        for article in articles:
            vector = self._vectors[(tenant_id, article.article_id)]
            score = sum(x * y for x, y in zip(q, vector, strict=True))
            if needle in article.passage_text().casefold():
                score += KEYWORD_BONUS
            hits.append(SearchHit(article, score))
        hits.sort(key=lambda h: (-h.score, h.article.article_id))
        return hits[:limit]
