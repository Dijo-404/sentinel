"""Optional PostgreSQL assistant persistence. Used when ASSISTANT_DATABASE_URL is set."""

from __future__ import annotations

from sqlalchemy import Column, MetaData, String, Table, Text, create_engine, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

from ..application.errors import ConfigurationError
from ..domain.types import Message, Thread, ThreadAudience


def assistant_tables(schema: str) -> tuple[Table, Table]:
    metadata = MetaData()
    threads = Table(
        "assistant_threads",
        metadata,
        Column("thread_id", String(128), primary_key=True),
        Column("tenant_id", String(256), nullable=False),
        Column("role", String(32), nullable=False),
        Column("title", Text, nullable=False),
        Column("created_at", String(64), nullable=False),
        Column("updated_at", String(64), nullable=False),
        Column("created_by", String(256), nullable=False),
        schema=schema,
    )
    messages = Table(
        "assistant_messages",
        metadata,
        Column("message_id", String(128), primary_key=True),
        Column("thread_id", String(128), nullable=False),
        Column("tenant_id", String(256), nullable=False),
        Column("role", String(32), nullable=False),
        Column("text", Text, nullable=False),
        Column("evidence_mode", String(64), nullable=False),
        Column("created_at", String(64), nullable=False),
        Column("principal_id", String(256), nullable=True),
        schema=schema,
    )
    return threads, messages


def build_engine(database_url: str) -> Engine:
    engine = create_engine(database_url)
    if engine.dialect.name != "postgresql":
        raise ConfigurationError("A real PostgreSQL connection is required")
    return engine


class PostgresAssistantStore:
    def __init__(self, engine: Engine, schema: str = "assistant"):
        if engine.dialect.name != "postgresql":
            raise ConfigurationError("A real PostgreSQL connection is required")
        self._engine = engine
        self._schema = schema
        self._threads, self._messages = assistant_tables(schema)

    def migrate(self) -> None:
        with self._engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{self._schema}"'))
            self._threads.create(connection, checkfirst=True)
            self._messages.create(connection, checkfirst=True)

    def create_thread(self, thread: Thread) -> Thread:
        with self._engine.begin() as connection:
            connection.execute(pg_insert(self._threads).values(**_thread_row(thread)))
        return thread

    def list_threads(self, *, tenant_id: str, role: ThreadAudience) -> tuple[Thread, ...]:
        with self._engine.begin() as connection:
            rows = (
                connection.execute(
                    select(self._threads)
                    .where(self._threads.c.tenant_id == tenant_id)
                    .where(self._threads.c.role == role)
                    .order_by(self._threads.c.updated_at.desc())
                )
                .mappings()
                .all()
            )
        return tuple(_thread_from_row(row) for row in rows)

    def get_thread(self, thread_id: str) -> Thread | None:
        with self._engine.begin() as connection:
            row = (
                connection.execute(
                    select(self._threads).where(self._threads.c.thread_id == thread_id)
                )
                .mappings()
                .first()
            )
        return None if row is None else _thread_from_row(row)

    def touch_thread(self, thread_id: str, *, updated_at: str) -> Thread:
        with self._engine.begin() as connection:
            connection.execute(
                self._threads.update()
                .where(self._threads.c.thread_id == thread_id)
                .values(updated_at=updated_at)
            )
            row = (
                connection.execute(
                    select(self._threads).where(self._threads.c.thread_id == thread_id)
                )
                .mappings()
                .one()
            )
        return _thread_from_row(row)

    def add_message(self, message: Message) -> Message:
        with self._engine.begin() as connection:
            connection.execute(pg_insert(self._messages).values(**_message_row(message)))
        return message

    def list_messages(self, *, thread_id: str, tenant_id: str) -> tuple[Message, ...]:
        with self._engine.begin() as connection:
            rows = (
                connection.execute(
                    select(self._messages)
                    .where(self._messages.c.thread_id == thread_id)
                    .where(self._messages.c.tenant_id == tenant_id)
                    .order_by(self._messages.c.created_at.asc())
                )
                .mappings()
                .all()
            )
        return tuple(_message_from_row(row) for row in rows)

    def upsert_seed_bundle(self, thread: Thread, messages: tuple[Message, ...]) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                pg_insert(self._threads)
                .values(**_thread_row(thread))
                .on_conflict_do_update(
                    index_elements=["thread_id"],
                    set_={
                        "tenant_id": thread.tenant_id,
                        "role": thread.role,
                        "title": thread.title,
                        "created_at": thread.created_at,
                        "updated_at": thread.updated_at,
                        "created_by": thread.created_by,
                    },
                )
            )
            for message in messages:
                connection.execute(
                    pg_insert(self._messages)
                    .values(**_message_row(message))
                    .on_conflict_do_update(
                        index_elements=["message_id"],
                        set_={
                            "thread_id": message.thread_id,
                            "tenant_id": message.tenant_id,
                            "role": message.role,
                            "text": message.text,
                            "evidence_mode": message.evidence_mode,
                            "created_at": message.created_at,
                            "principal_id": message.principal_id,
                        },
                    )
                )


def _thread_row(thread: Thread) -> dict:
    return {
        "thread_id": thread.thread_id,
        "tenant_id": thread.tenant_id,
        "role": thread.role,
        "title": thread.title,
        "created_at": thread.created_at,
        "updated_at": thread.updated_at,
        "created_by": thread.created_by,
    }


def _message_row(message: Message) -> dict:
    return {
        "message_id": message.message_id,
        "thread_id": message.thread_id,
        "tenant_id": message.tenant_id,
        "role": message.role,
        "text": message.text,
        "evidence_mode": message.evidence_mode,
        "created_at": message.created_at,
        "principal_id": message.principal_id,
    }


def _thread_from_row(row) -> Thread:
    return Thread(
        thread_id=row["thread_id"],
        tenant_id=row["tenant_id"],
        role=row["role"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        created_by=row["created_by"],
    )


def _message_from_row(row) -> Message:
    return Message(
        message_id=row["message_id"],
        thread_id=row["thread_id"],
        tenant_id=row["tenant_id"],
        role=row["role"],
        text=row["text"],
        evidence_mode=row["evidence_mode"],
        created_at=row["created_at"],
        principal_id=row["principal_id"],
    )
