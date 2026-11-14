"""SQLite inbox store for durable real-peers runs (stdlib only)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from sentinel_merchant_inbox.contracts import (
    ExceptionItem,
    ExceptionKind,
    ExceptionStatus,
    parse_exception_item,
)
from sentinel_merchant_inbox.domain import rules


def sqlite_path_from_url(database_url: str) -> Path:
    url = database_url.strip()
    if not url:
        raise ValueError("database URL is empty")
    if url.startswith("sqlite:///"):
        return Path(url.removeprefix("sqlite:///"))
    return Path(url)


class SqliteInboxStore:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        if self._path.parent and str(self._path.parent) not in {"", "."}:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @classmethod
    def from_url(cls, database_url: str) -> SqliteInboxStore:
        return cls(sqlite_path_from_url(database_url))

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS exception_items (
                    tenant_id TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    body_json TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, item_id)
                )
                """
            )
            conn.commit()

    def list_items(
        self,
        *,
        tenant_id: str,
        merchant_ref: str,
        kind: ExceptionKind | None = None,
        status: ExceptionStatus | None = None,
    ) -> list[ExceptionItem]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT body_json FROM exception_items WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchall()
        out: list[ExceptionItem] = []
        for row in rows:
            item = parse_exception_item(json.loads(row["body_json"]))
            if item.merchant_ref != merchant_ref:
                continue
            if not rules.matches_filters(item, kind=kind, status=status):
                continue
            out.append(item)
        out.sort(key=lambda i: i.item_id)
        return out

    def get_item(self, *, tenant_id: str, item_id: str) -> ExceptionItem | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT body_json FROM exception_items
                WHERE tenant_id = ? AND item_id = ?
                """,
                (tenant_id, item_id),
            ).fetchone()
        if row is None:
            return None
        return parse_exception_item(json.loads(row["body_json"]))

    def save_item(self, item: ExceptionItem) -> ExceptionItem:
        payload = json.dumps(item.as_dict())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO exception_items (tenant_id, item_id, body_json)
                VALUES (?, ?, ?)
                ON CONFLICT(tenant_id, item_id) DO UPDATE SET body_json = excluded.body_json
                """,
                (item.tenant_id, item.item_id, payload),
            )
            conn.commit()
        return parse_exception_item(json.loads(payload))
