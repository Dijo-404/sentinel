"""SQLite request store for durable real-peers runs (stdlib only)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from sentinel_merchant_refunds.domain.types import MerchantRefundRequest


def sqlite_path_from_url(database_url: str) -> Path:
    url = database_url.strip()
    if not url:
        raise ValueError("database URL is empty")
    if url.startswith("sqlite:///"):
        return Path(url.removeprefix("sqlite:///"))
    return Path(url)


class SqliteRequestStore:
    """JSON-row SQLite store shared across workers via a filesystem path."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        if self._path.parent and str(self._path.parent) not in {"", "."}:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @classmethod
    def from_url(cls, database_url: str) -> SqliteRequestStore:
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
                CREATE TABLE IF NOT EXISTS refund_requests (
                    tenant_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    body_json TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, request_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS refund_idempotency (
                    tenant_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, idempotency_key)
                )
                """
            )
            conn.commit()

    def put(self, request: MerchantRefundRequest) -> None:
        payload = request.model_dump_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO refund_requests (tenant_id, request_id, body_json)
                VALUES (?, ?, ?)
                ON CONFLICT(tenant_id, request_id) DO UPDATE SET body_json = excluded.body_json
                """,
                (request.tenant_id, request.request_id, payload),
            )
            conn.commit()

    def get(self, tenant_id: str, request_id: str) -> MerchantRefundRequest | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT body_json FROM refund_requests
                WHERE tenant_id = ? AND request_id = ?
                """,
                (tenant_id, request_id),
            ).fetchone()
        if row is None:
            return None
        return MerchantRefundRequest.model_validate_json(row["body_json"])

    def get_by_idempotency(
        self, tenant_id: str, idempotency_key: str
    ) -> MerchantRefundRequest | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT request_id FROM refund_idempotency
                WHERE tenant_id = ? AND idempotency_key = ?
                """,
                (tenant_id, idempotency_key),
            ).fetchone()
        if row is None:
            return None
        return self.get(tenant_id, row["request_id"])

    def put_idempotency(
        self, tenant_id: str, idempotency_key: str, request: MerchantRefundRequest
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO refund_idempotency (tenant_id, idempotency_key, request_id)
                VALUES (?, ?, ?)
                ON CONFLICT(tenant_id, idempotency_key) DO UPDATE SET
                    request_id = excluded.request_id
                """,
                (tenant_id, idempotency_key, request.request_id),
            )
            conn.execute(
                """
                INSERT INTO refund_requests (tenant_id, request_id, body_json)
                VALUES (?, ?, ?)
                ON CONFLICT(tenant_id, request_id) DO UPDATE SET body_json = excluded.body_json
                """,
                (tenant_id, request.request_id, request.model_dump_json()),
            )
            conn.commit()
