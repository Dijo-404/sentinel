"""In-process article store for fixture/tests."""

from __future__ import annotations

from ..domain.types import Article


class MemoryArticleStore:
    def __init__(self) -> None:
        self._by_id: dict[tuple[str, str], Article] = {}

    def upsert(self, article: Article) -> None:
        self._by_id[(article.tenant_id, article.article_id)] = article

    def list_articles(self, tenant_id: str) -> list[Article]:
        rows = [a for (tid, _), a in self._by_id.items() if tid == tenant_id]
        return sorted(rows, key=lambda a: a.updated_at, reverse=True)

    def get_article(self, tenant_id: str, article_id: str) -> Article | None:
        return self._by_id.get((tenant_id, article_id))

    def search_articles(self, tenant_id: str, query: str) -> list[Article]:
        needle = query.casefold()
        hits: list[Article] = []
        for article in self.list_articles(tenant_id):
            hay = f"{article.title}\n{article.summary}\n{article.body}".casefold()
            if needle in hay:
                hits.append(article)
        return hits
