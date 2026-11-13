"""Durable dispatcher bookkeeping. Never stores competing financial balances."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, text

from sentinel_dispatcher.domain.types import DispatchJob

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS {schema}.dispatch_jobs (
    tenant_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    provider_ref TEXT NOT NULL,
    lease_id TEXT NOT NULL,
    action_digest TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    phase TEXT NOT NULL,
    same_key_retry BOOLEAN NOT NULL,
    status_lookup BOOLEAN NOT NULL,
    provider_status TEXT,
    outcome_status TEXT,
    reason_code TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, action_id),
    UNIQUE (tenant_id, provider_ref)
)
"""


def ensure_schema(engine: Engine, schema: str) -> None:
    if not schema.replace("_", "").isalnum():
        raise ValueError("Invalid schema name")
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        connection.execute(text(SCHEMA_DDL.format(schema=f'"{schema}"')))


class PostgresWorkerStore:
    def __init__(self, engine: Engine, *, schema: str) -> None:
        if not schema.replace("_", "").isalnum():
            raise ValueError("Invalid schema name")
        self._engine = engine
        self._schema = schema

    def save(self, job: DispatchJob) -> None:
        now = datetime.now(tz=UTC).isoformat()
        sql = text(
            f"""
            INSERT INTO "{self._schema}".dispatch_jobs AS j (
                tenant_id, action_id, provider_ref, lease_id, action_digest,
                payload_json, phase, same_key_retry, status_lookup,
                provider_status, outcome_status, reason_code, created_at, updated_at
            ) VALUES (
                :tenant_id, :action_id, :provider_ref, :lease_id, :action_digest,
                :payload_json, :phase, :same_key_retry, :status_lookup,
                :provider_status, :outcome_status, :reason_code, :created_at, :updated_at
            )
            ON CONFLICT (tenant_id, action_id) DO UPDATE SET
                provider_ref = EXCLUDED.provider_ref,
                lease_id = EXCLUDED.lease_id,
                action_digest = EXCLUDED.action_digest,
                payload_json = EXCLUDED.payload_json,
                phase = EXCLUDED.phase,
                same_key_retry = EXCLUDED.same_key_retry,
                status_lookup = EXCLUDED.status_lookup,
                provider_status = EXCLUDED.provider_status,
                outcome_status = EXCLUDED.outcome_status,
                reason_code = EXCLUDED.reason_code,
                updated_at = EXCLUDED.updated_at
            """
        )
        params = self._params(job, now=now)
        with self._engine.begin() as connection:
            connection.execute(sql, params)

    def get(self, tenant_id: str, action_id: str) -> DispatchJob | None:
        sql = text(
            f"""
            SELECT tenant_id, action_id, provider_ref, lease_id, action_digest,
                   payload_json, phase, same_key_retry, status_lookup,
                   provider_status, outcome_status, reason_code
            FROM "{self._schema}".dispatch_jobs
            WHERE tenant_id = :tenant_id AND action_id = :action_id
            """
        )
        with self._engine.connect() as connection:
            row = (
                connection.execute(sql, {"tenant_id": tenant_id, "action_id": action_id})
                .mappings()
                .first()
            )
        return None if row is None else self._from_row(row)

    def list_incomplete(self, tenant_id: str) -> list[DispatchJob]:
        # SUBMITTED / RECONCILING after timeout stay here until reconcile completes.
        sql = text(
            f"""
            SELECT tenant_id, action_id, provider_ref, lease_id, action_digest,
                   payload_json, phase, same_key_retry, status_lookup,
                   provider_status, outcome_status, reason_code
            FROM "{self._schema}".dispatch_jobs
            WHERE tenant_id = :tenant_id
              AND phase NOT IN ('OUTCOME_REPORTED', 'ESCALATED')
            ORDER BY created_at ASC
            """
        )
        with self._engine.connect() as connection:
            rows = connection.execute(sql, {"tenant_id": tenant_id}).mappings().all()
        return [self._from_row(row) for row in rows]

    def _params(self, job: DispatchJob, *, now: str) -> dict[str, Any]:
        return {
            "tenant_id": job.tenant_id,
            "action_id": job.action_id,
            "provider_ref": job.provider_ref,
            "lease_id": job.lease_id,
            "action_digest": job.action_digest,
            "payload_json": json.dumps(dict(job.payload), separators=(",", ":"), sort_keys=True),
            "phase": job.phase,
            "same_key_retry": job.same_key_retry,
            "status_lookup": job.status_lookup,
            "provider_status": job.provider_status,
            "outcome_status": job.outcome_status,
            "reason_code": job.reason_code,
            "created_at": now,
            "updated_at": now,
        }

    def _from_row(self, row: Any) -> DispatchJob:
        return DispatchJob(
            tenant_id=row["tenant_id"],
            action_id=row["action_id"],
            provider_ref=row["provider_ref"],
            lease_id=row["lease_id"],
            action_digest=row["action_digest"],
            payload=json.loads(row["payload_json"]),
            phase=row["phase"],
            same_key_retry=bool(row["same_key_retry"]),
            status_lookup=bool(row["status_lookup"]),
            provider_status=row["provider_status"],
            outcome_status=row["outcome_status"],
            reason_code=row["reason_code"],
        )
