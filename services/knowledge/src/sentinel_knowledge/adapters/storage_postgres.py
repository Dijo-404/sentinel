"""PostgreSQL article store (KNOWLEDGE_DATABASE_URL)."""

from __future__ import annotations

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
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from ..application.errors import ConfigurationError, PeerUnavailableError
from ..domain.types import Article

SCHEMA = "knowledge"
TABLE = "articles"


def build_engine(database_url: str) -> Engine:
    engine = create_engine(database_url, hide_parameters=True)
    if engine.dialect.name != "postgresql":
        raise ConfigurationError("KNOWLEDGE_DATABASE_URL must be PostgreSQL")
    return engine


def _table(schema: str = SCHEMA) -> Table:
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
        schema=schema,
    )


class PostgresArticleStore:
    def __init__(self, engine: Engine, schema: str = SCHEMA) -> None:
        if engine.dialect.name != "postgresql":
            raise ConfigurationError("A real PostgreSQL connection is required")
        self._engine = engine
        self._schema = schema
        self._table = _table(schema)

    def migrate(self) -> None:
        try:
            with self._engine.begin() as connection:
                connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{self._schema}"'))
                self._table.create(connection, checkfirst=True)
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("knowledge database unavailable") from exc

    def upsert(self, article: Article) -> None:
        values = {
            "tenant_id": article.tenant_id,
            "article_id": article.article_id,
            "title": article.title,
            "summary": article.summary,
            "body": article.body,
            "updated_at": article.updated_at,
        }
        stmt = pg_insert(self._table).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["tenant_id", "article_id"],
            set_={
                "title": stmt.excluded.title,
                "summary": stmt.excluded.summary,
                "body": stmt.excluded.body,
                "updated_at": stmt.excluded.updated_at,
            },
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

    def search_articles(self, tenant_id: str, query: str) -> list[Article]:
        pattern = f"%{query}%"
        try:
            with self._engine.begin() as connection:
                rows = (
                    connection.execute(
                        select(self._table)
                        .where(
                            self._table.c.tenant_id == tenant_id,
                            or_(
                                self._table.c.title.ilike(pattern),
                                self._table.c.summary.ilike(pattern),
                                self._table.c.body.ilike(pattern),
                            ),
                        )
                        .order_by(self._table.c.updated_at.desc())
                    )
                    .mappings()
                    .all()
                )
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("knowledge database unavailable") from exc
        return [_row_to_article(dict(row)) for row in rows]


def _row_to_article(row: dict) -> Article:
    return Article(
        article_id=row["article_id"],
        tenant_id=row["tenant_id"],
        title=row["title"],
        summary=row["summary"],
        body=row["body"],
        updated_at=row["updated_at"],
    )
