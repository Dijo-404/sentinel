"""SQLite SLA store for durable real-peers runs (stdlib only)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from sentinel_merchant_sla.contracts import SlaPolicy, SlaTask


def sqlite_path_from_url(database_url: str) -> Path:
    url = database_url.strip()
    if not url:
        raise ValueError("database URL is empty")
    if url.startswith("sqlite:///"):
        return Path(url.removeprefix("sqlite:///"))
    return Path(url)


class SqliteSlaStore:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        if self._path.parent and str(self._path.parent) not in {"", "."}:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @classmethod
    def from_url(cls, database_url: str) -> SqliteSlaStore:
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
                CREATE TABLE IF NOT EXISTS sla_policies (
                    policy_id TEXT PRIMARY KEY,
                    body_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sla_tasks (
                    task_id TEXT PRIMARY KEY,
                    body_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sla_counters (
                    prefix TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                )
                """
            )
            conn.commit()

    def put_policy(self, policy: SlaPolicy) -> SlaPolicy:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sla_policies (policy_id, body_json) VALUES (?, ?)
                ON CONFLICT(policy_id) DO UPDATE SET body_json = excluded.body_json
                """,
                (policy.policy_id, json.dumps(policy.as_dict())),
            )
            conn.commit()
        return policy

    def get_policy(self, policy_id: str) -> SlaPolicy | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT body_json FROM sla_policies WHERE policy_id = ?",
                (policy_id,),
            ).fetchone()
        if row is None:
            return None
        return SlaPolicy(**json.loads(row["body_json"]))

    def list_policies(self, *, tenant_id: str, merchant_ref: str) -> list[SlaPolicy]:
        with self._connect() as conn:
            rows = conn.execute("SELECT body_json FROM sla_policies").fetchall()
        out: list[SlaPolicy] = []
        for row in rows:
            policy = SlaPolicy(**json.loads(row["body_json"]))
            if policy.tenant_id == tenant_id and policy.merchant_ref == merchant_ref:
                out.append(policy)
        return out

    def put_task(self, task: SlaTask) -> SlaTask:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sla_tasks (task_id, body_json) VALUES (?, ?)
                ON CONFLICT(task_id) DO UPDATE SET body_json = excluded.body_json
                """,
                (task.task_id, json.dumps(task.as_dict())),
            )
            conn.commit()
        return task

    def get_task(self, task_id: str) -> SlaTask | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT body_json FROM sla_tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        return SlaTask(**json.loads(row["body_json"]))

    def list_tasks(
        self,
        *,
        tenant_id: str,
        merchant_ref: str | None = None,
        case_id: str | None = None,
    ) -> list[SlaTask]:
        with self._connect() as conn:
            rows = conn.execute("SELECT body_json FROM sla_tasks").fetchall()
        out: list[SlaTask] = []
        for row in rows:
            task = SlaTask(**json.loads(row["body_json"]))
            if task.tenant_id is not None and task.tenant_id != tenant_id:
                continue
            if merchant_ref is not None and task.merchant_ref != merchant_ref:
                continue
            if case_id is not None and task.case_id != case_id:
                continue
            out.append(task)
        return out

    def next_id(self, prefix: str) -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM sla_counters WHERE prefix = ?",
                (prefix,),
            ).fetchone()
            n = (row["value"] if row is not None else 0) + 1
            conn.execute(
                """
                INSERT INTO sla_counters (prefix, value) VALUES (?, ?)
                ON CONFLICT(prefix) DO UPDATE SET value = excluded.value
                """,
                (prefix, n),
            )
            conn.commit()
        return f"{prefix}-{n}"
