"""PostgreSQL + pgvector article store (KNOWLEDGE_DATABASE_URL).

Search is semantic: cosine similarity over local embeddings (HNSW index) unioned with
literal keyword matches, re-ranked by cosine + keyword bonus. There is no substring
fallback: a missing `vector` extension or embedder fails closed.
"""

from __future__ import annotations

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    or_,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError

from ..application.errors import ConfigurationError, PeerUnavailableError
from ..application.ports import Embedder
from ..domain.types import KEYWORD_BONUS, Article, SearchHit

SCHEMA = "knowledge"
TABLE = "articles"
MIN_PGVECTOR = (0, 8)  # hnsw.iterative_scan keeps tenant-filtered ANN results complete
REINDEX_BATCH = 32


def build_engine(database_url: str) -> Engine:
    engine = create_engine(database_url, hide_parameters=True)
    if engine.dialect.name != "postgresql":
        raise ConfigurationError("KNOWLEDGE_DATABASE_URL must be PostgreSQL")
    return engine


def _table(dimension: int, schema: str = SCHEMA) -> Table:
    metadata = MetaData()
    return Table(
        TABLE,
        metadata,
        Column("tenant_id", String(256), primary_key=True),
        Column("article_id", String(128), primary_key=True),
        Column("title", String(512), nullable=False),
        Column("summary", Text, nullable=False),
        Column("body", Text, nullable=False),
        Column("updated_at", String(64), nullable=False),
        Column("embedding", Vector(dimension), nullable=True),
        Column("embedding_model", String(256), nullable=True),
        schema=schema,
    )


class PostgresArticleStore:
    def __init__(self, engine: Engine, embedder: Embedder, schema: str = SCHEMA) -> None:
        if engine.dialect.name != "postgresql":
            raise ConfigurationError("A real PostgreSQL connection is required")
        if embedder is None:
            raise ConfigurationError("PostgresArticleStore requires an embedder")
        self._engine = engine
        self._embedder = embedder
        self._schema = schema
        self._table = _table(embedder.dimension, schema)
        self._qualified = f'"{schema}"."{TABLE}"'
        self.search_mode = "semantic-hybrid"

    def migrate(self, *, reset_dimension: bool = False) -> None:
        """Idempotent DDL. Fails closed if pgvector is missing or too old.

        A dimension change (new embedding model) needs ``reset_dimension=True``, which
        drops the old vectors; ``reindex`` then recomputes them.
        """
        dim = self._embedder.dimension
        try:
            with self._engine.begin() as connection:
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                version = connection.execute(
                    text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
                ).scalar_one()
                if tuple(int(p) for p in version.split(".")[:2]) < MIN_PGVECTOR:
                    raise ConfigurationError(f"pgvector >= 0.8 required, found {version}")
                connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{self._schema}"'))
                self._table.create(connection, checkfirst=True)
                connection.execute(
                    text(
                        f"ALTER TABLE {self._qualified} "
                        f"ADD COLUMN IF NOT EXISTS embedding vector({dim}), "
                        "ADD COLUMN IF NOT EXISTS embedding_model varchar(256)"
                    )
                )
                current = _column_dimension(connection, self._schema)
                if current != dim:
                    if not reset_dimension:
                        raise ConfigurationError(
                            f"embedding column is vector({current}) but model "
                            f"{self._embedder.model_name} has {dim} dims; "
                            "run `sentinel-knowledge reindex`"
                        )
                    connection.execute(text(f"ALTER TABLE {self._qualified} DROP COLUMN embedding"))
                    connection.execute(
                        text(f"ALTER TABLE {self._qualified} ADD COLUMN embedding vector({dim})")
                    )
                    connection.execute(text(f"UPDATE {self._qualified} SET embedding_model = NULL"))
                connection.execute(
                    text(
                        f"CREATE INDEX IF NOT EXISTS {TABLE}_embedding_hnsw "
                        f"ON {self._qualified} USING hnsw (embedding vector_cosine_ops)"
                    )
                )
        except SQLAlchemyError as exc:
            raise PeerUnavailableError(
                "knowledge database unavailable or pgvector extension missing"
            ) from exc

    def reindex(self, *, force: bool = False) -> int:
        """Embed rows with no vector or a vector from another model. Returns rows updated."""
        model = self._embedder.model_name
        t = self._table
        stale = or_(t.c.embedding.is_(None), t.c.embedding_model.is_distinct_from(model))
        where = None if force else stale
        updated = 0
        try:
            with self._engine.begin() as connection:
                query = select(t.c.tenant_id, t.c.article_id, t.c.title, t.c.summary, t.c.body)
                if where is not None:
                    query = query.where(where)
                rows = connection.execute(query).all()
            for start in range(0, len(rows), REINDEX_BATCH):
                batch = rows[start : start + REINDEX_BATCH]
                vectors = self._embedder.embed_passages(
                    [f"{r.title}\n{r.summary}\n{r.body}" for r in batch]
                )
                with self._engine.begin() as connection:
                    for row, vector in zip(batch, vectors, strict=True):
                        connection.execute(
                            t.update()
                            .where(
                                t.c.tenant_id == row.tenant_id,
                                t.c.article_id == row.article_id,
                            )
                            .values(embedding=vector, embedding_model=model)
                        )
                updated += len(batch)
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("knowledge database unavailable") from exc
        return updated

    def upsert(self, article: Article) -> None:
        # Embed before writing so a failed embedding never leaves a stale vector behind.
        vector = self._embedder.embed_passages([article.passage_text()])[0]
        values = {
            "tenant_id": article.tenant_id,
            "article_id": article.article_id,
            "title": article.title,
            "summary": article.summary,
            "body": article.body,
            "updated_at": article.updated_at,
            "embedding": vector,
            "embedding_model": self._embedder.model_name,
        }
        stmt = pg_insert(self._table).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["tenant_id", "article_id"],
            set_={k: stmt.excluded[k] for k in values if k not in ("tenant_id", "article_id")},
        )
        try:
            with self._engine.begin() as connection:
                connection.execute(stmt)
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("knowledge database unavailable") from exc

    def list_articles(self, tenant_id: str) -> list[Article]:
        try:
            with self._engine.begin() as connection:
                rows = (
                    connection.execute(
                        select(self._table)
                        .where(self._table.c.tenant_id == tenant_id)
                        .order_by(self._table.c.updated_at.desc())
                    )
                    .mappings()
                    .all()
                )
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("knowledge database unavailable") from exc
        return [_row_to_article(dict(row)) for row in rows]

    def get_article(self, tenant_id: str, article_id: str) -> Article | None:
        try:
            with self._engine.begin() as connection:
                row = (
                    connection.execute(
                        select(self._table).where(
                            self._table.c.tenant_id == tenant_id,
                            self._table.c.article_id == article_id,
                        )
                    )
                    .mappings()
                    .first()
                )
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("knowledge database unavailable") from exc
        if row is None:
            return None
        return _row_to_article(dict(row))

    def search_articles(self, tenant_id: str, query: str, limit: int) -> list[SearchHit]:
        query_vector = self._embedder.embed_query(query)
        pattern = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        keyword = "(a.title ILIKE :pattern OR a.summary ILIKE :pattern OR a.body ILIKE :pattern)"
        # Only vectors from the active model are comparable; tenant scope on every branch.
        scoped = "a.tenant_id = :tenant_id AND a.embedding_model = :model"
        sql = text(
            f"""
            WITH q AS (SELECT CAST(:qvec AS vector) AS v),
            vec AS (
                SELECT a.article_id FROM {self._qualified} a, q
                WHERE {scoped}
                ORDER BY a.embedding <=> q.v
                LIMIT :candidates
            ),
            kw AS (
                SELECT a.article_id FROM {self._qualified} a
                WHERE {scoped} AND {keyword}
                LIMIT :candidates
            )
            SELECT a.tenant_id, a.article_id, a.title, a.summary, a.body, a.updated_at,
                   (1 - (a.embedding <=> q.v))
                     + CASE WHEN {keyword} THEN :bonus ELSE 0 END AS score
            FROM {self._qualified} a, q
            WHERE {scoped}
              AND a.article_id IN (SELECT article_id FROM vec UNION SELECT article_id FROM kw)
            ORDER BY score DESC, a.article_id
            LIMIT :limit
            """
        )
        params = {
            "qvec": "[" + ",".join(repr(float(x)) for x in query_vector) + "]",
            "pattern": pattern,
            "tenant_id": tenant_id,
            "model": self._embedder.model_name,
            "candidates": max(limit * 4, 40),
            "bonus": KEYWORD_BONUS,
            "limit": limit,
        }
        try:
            with self._engine.begin() as connection:
                connection.execute(text("SET LOCAL hnsw.iterative_scan = relaxed_order"))
                rows = connection.execute(sql, params).mappings().all()
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("knowledge database unavailable") from exc
        return [SearchHit(_row_to_article(dict(row)), float(row["score"])) for row in rows]


def _column_dimension(connection: Connection, schema: str) -> int:
    return connection.execute(
        text(
            "SELECT atttypmod FROM pg_attribute "
            "WHERE attrelid = CAST(:rel AS regclass) AND attname = 'embedding' "
            "AND NOT attisdropped"
        ),
        {"rel": f'"{schema}"."{TABLE}"'},
    ).scalar_one()


def _row_to_article(row: dict) -> Article:
    return Article(
        article_id=row["article_id"],
        tenant_id=row["tenant_id"],
        title=row["title"],
        summary=row["summary"],
        body=row["body"],
        updated_at=row["updated_at"],
    )
