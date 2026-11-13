"""Durable verifier inbox/recheck/assessment storage."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import Engine, text

from sentinel_verifier.domain.types import (
    InboxRecord,
    ProviderBinding,
    RecheckJob,
    VerificationResult,
)

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS {schema}.webhook_inbox (
    tenant_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'simulator',
    provider_ref TEXT NOT NULL,
    event_type TEXT NOT NULL,
    merchant_ref TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    payload_json TEXT NOT NULL,
    signature_hex TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL,
    processed_at TIMESTAMPTZ,
    process_status TEXT NOT NULL DEFAULT 'ACCEPTED',
    reason_code TEXT,
    PRIMARY KEY (tenant_id, event_id)
);
CREATE TABLE IF NOT EXISTS {schema}.recheck_jobs (
    tenant_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    case_id TEXT NOT NULL,
    case_revision INT NOT NULL,
    action_id TEXT NOT NULL,
    provider_ref TEXT NOT NULL,
    request_digest TEXT NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    lease_expires_at TIMESTAMPTZ,
    attempts INT NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, job_id),
    UNIQUE (tenant_id, idempotency_key)
);
CREATE TABLE IF NOT EXISTS {schema}.assessments (
    tenant_id TEXT NOT NULL,
    assessment_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    case_revision INT NOT NULL,
    action_id TEXT NOT NULL,
    provider_ref TEXT NOT NULL,
    assessed_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    reason_codes_json TEXT NOT NULL,
    PRIMARY KEY (tenant_id, assessment_id)
);
CREATE TABLE IF NOT EXISTS {schema}.provider_bindings (
    tenant_id TEXT NOT NULL,
    provider_ref TEXT NOT NULL,
    action_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    case_revision INT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, provider_ref)
);
"""


def ensure_schema(engine: Engine, schema: str) -> None:
    if not schema.replace("_", "").isalnum():
        raise ValueError("Invalid schema name")
    quoted = f'"{schema}"'
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {quoted}"))
        for statement in SCHEMA_DDL.format(schema=quoted).split(";"):
            stmt = statement.strip()
            if stmt:
                connection.execute(text(stmt))


class PostgresVerifierStore:
    def __init__(self, engine: Engine, *, schema: str) -> None:
        if not schema.replace("_", "").isalnum():
            raise ValueError("Invalid schema name")
        self._engine = engine
        self._schema = schema

    def insert_inbox(self, record: InboxRecord) -> InboxRecord:
        sql = text(
            f"""
            INSERT INTO "{self._schema}".webhook_inbox (
                tenant_id, event_id, provider, provider_ref, event_type, merchant_ref,
                occurred_at, payload_json, signature_hex, received_at, processed_at,
                process_status, reason_code
            ) VALUES (
                :tenant_id, :event_id, :provider, :provider_ref, :event_type, :merchant_ref,
                :occurred_at, :payload_json, :signature_hex, :received_at, :processed_at,
                :process_status, :reason_code
            )
            ON CONFLICT (tenant_id, event_id) DO NOTHING
            RETURNING event_id
            """
        )
        with self._engine.begin() as connection:
            row = connection.execute(sql, _inbox_params(record)).first()
        if row is None:
            existing = self.get_inbox(record.tenant_id, record.event_id)
            assert existing is not None
            return InboxRecord(
                tenant_id=existing.tenant_id,
                event_id=existing.event_id,
                provider=existing.provider,
                provider_ref=existing.provider_ref,
                event_type=existing.event_type,
                merchant_ref=existing.merchant_ref,
                occurred_at=existing.occurred_at,
                payload_json=existing.payload_json,
                signature_hex=existing.signature_hex,
                received_at=existing.received_at,
                processed_at=existing.processed_at,
                process_status=existing.process_status,
                reason_code=existing.reason_code,
                duplicate=True,
            )
        return InboxRecord(
            tenant_id=record.tenant_id,
            event_id=record.event_id,
            provider=record.provider,
            provider_ref=record.provider_ref,
            event_type=record.event_type,
            merchant_ref=record.merchant_ref,
            occurred_at=record.occurred_at,
            payload_json=record.payload_json,
            signature_hex=record.signature_hex,
            received_at=record.received_at,
            processed_at=record.processed_at,
            process_status=record.process_status,
            reason_code=record.reason_code,
            duplicate=False,
        )

    def get_inbox(self, tenant_id: str, event_id: str) -> InboxRecord | None:
        sql = text(
            f"""
            SELECT tenant_id, event_id, provider, provider_ref, event_type, merchant_ref,
                   occurred_at, payload_json, signature_hex, received_at, processed_at,
                   process_status, reason_code
            FROM "{self._schema}".webhook_inbox
            WHERE tenant_id = :tenant_id AND event_id = :event_id
            """
        )
        with self._engine.connect() as connection:
            row = (
                connection.execute(sql, {"tenant_id": tenant_id, "event_id": event_id})
                .mappings()
                .first()
            )
        if row is None:
            return None
        return InboxRecord(
            tenant_id=row["tenant_id"],
            event_id=row["event_id"],
            provider=row["provider"],
            provider_ref=row["provider_ref"],
            event_type=row["event_type"],
            merchant_ref=row["merchant_ref"],
            occurred_at=_ts(row["occurred_at"]),
            payload_json=row["payload_json"],
            signature_hex=row["signature_hex"],
            received_at=_ts(row["received_at"]),
            processed_at=_ts(row["processed_at"]) if row["processed_at"] else None,
            process_status=row["process_status"],
            reason_code=row["reason_code"],
        )

    def mark_inbox_processed(
        self,
        tenant_id: str,
        event_id: str,
        *,
        process_status: str,
        reason_code: str | None,
        processed_at: str,
    ) -> None:
        sql = text(
            f"""
            UPDATE "{self._schema}".webhook_inbox
            SET process_status = :process_status,
                reason_code = :reason_code,
                processed_at = :processed_at
            WHERE tenant_id = :tenant_id AND event_id = :event_id
            """
        )
        with self._engine.begin() as connection:
            connection.execute(
                sql,
                {
                    "tenant_id": tenant_id,
                    "event_id": event_id,
                    "process_status": process_status,
                    "reason_code": reason_code,
                    "processed_at": processed_at,
                },
            )

    def save_recheck(self, job: RecheckJob) -> RecheckJob:
        sql = text(
            f"""
            INSERT INTO "{self._schema}".recheck_jobs (
                tenant_id, job_id, idempotency_key, case_id, case_revision, action_id,
                provider_ref, request_digest, available_at, lease_expires_at, attempts,
                status, created_at, updated_at
            ) VALUES (
                :tenant_id, :job_id, :idempotency_key, :case_id, :case_revision, :action_id,
                :provider_ref, :request_digest, :available_at, :lease_expires_at, :attempts,
                :status, :created_at, :updated_at
            )
            ON CONFLICT (tenant_id, job_id) DO UPDATE SET
                status = EXCLUDED.status,
                attempts = EXCLUDED.attempts,
                lease_expires_at = EXCLUDED.lease_expires_at,
                updated_at = EXCLUDED.updated_at
            """
        )
        with self._engine.begin() as connection:
            connection.execute(sql, _recheck_params(job))
        return job

    def get_recheck_by_idempotency(self, tenant_id: str, idempotency_key: str) -> RecheckJob | None:
        sql = text(
            f"""
            SELECT * FROM "{self._schema}".recheck_jobs
            WHERE tenant_id = :tenant_id AND idempotency_key = :idempotency_key
            """
        )
        with self._engine.connect() as connection:
            row = (
                connection.execute(
                    sql, {"tenant_id": tenant_id, "idempotency_key": idempotency_key}
                )
                .mappings()
                .first()
            )
        return _row_to_recheck(row) if row else None

    def get_recheck(self, tenant_id: str, job_id: str) -> RecheckJob | None:
        sql = text(
            f"""
            SELECT * FROM "{self._schema}".recheck_jobs
            WHERE tenant_id = :tenant_id AND job_id = :job_id
            """
        )
        with self._engine.connect() as connection:
            row = (
                connection.execute(sql, {"tenant_id": tenant_id, "job_id": job_id})
                .mappings()
                .first()
            )
        return _row_to_recheck(row) if row else None

    def save_assessment(self, result: VerificationResult, *, tenant_id: str) -> None:
        provider_ref = ""
        for item in result.evidence:
            facts = item.get("facts") or {}
            if facts.get("kind") == "REFUND":
                provider_ref = facts["refund"]["provider_ref"]
                break
        sql = text(
            f"""
            INSERT INTO "{self._schema}".assessments (
                tenant_id, assessment_id, case_id, case_revision, action_id, provider_ref,
                assessed_at, expires_at, status, evidence_json, reason_codes_json
            ) VALUES (
                :tenant_id, :assessment_id, :case_id, :case_revision, :action_id, :provider_ref,
                :assessed_at, :expires_at, :status, :evidence_json, :reason_codes_json
            )
            ON CONFLICT (tenant_id, assessment_id) DO NOTHING
            """
        )
        with self._engine.begin() as connection:
            connection.execute(
                sql,
                {
                    "tenant_id": tenant_id,
                    "assessment_id": result.assessment_id,
                    "case_id": result.case_id,
                    "case_revision": result.case_revision,
                    "action_id": result.action_id,
                    "provider_ref": provider_ref,
                    "assessed_at": result.assessed_at,
                    "expires_at": result.expires_at,
                    "status": result.status,
                    "evidence_json": json.dumps(list(result.evidence)),
                    "reason_codes_json": json.dumps(list(result.reason_codes)),
                },
            )

    def get_assessment(self, tenant_id: str, assessment_id: str) -> VerificationResult | None:
        sql = text(
            f"""
            SELECT * FROM "{self._schema}".assessments
            WHERE tenant_id = :tenant_id AND assessment_id = :assessment_id
            """
        )
        with self._engine.connect() as connection:
            row = (
                connection.execute(sql, {"tenant_id": tenant_id, "assessment_id": assessment_id})
                .mappings()
                .first()
            )
        if row is None:
            return None
        return VerificationResult(
            assessment_id=row["assessment_id"],
            case_id=row["case_id"],
            case_revision=int(row["case_revision"]),
            action_id=row["action_id"],
            assessed_at=_ts(row["assessed_at"]),
            expires_at=_ts(row["expires_at"]),
            status=row["status"],
            evidence=tuple(json.loads(row["evidence_json"])),
            reason_codes=tuple(json.loads(row["reason_codes_json"])),
        )

    def save_binding(self, binding: ProviderBinding) -> None:
        sql = text(
            f"""
            INSERT INTO "{self._schema}".provider_bindings (
                tenant_id, provider_ref, action_id, case_id, case_revision, updated_at
            ) VALUES (
                :tenant_id, :provider_ref, :action_id, :case_id, :case_revision, :updated_at
            )
            ON CONFLICT (tenant_id, provider_ref) DO UPDATE SET
                action_id = EXCLUDED.action_id,
                case_id = EXCLUDED.case_id,
                case_revision = EXCLUDED.case_revision,
                updated_at = EXCLUDED.updated_at
            """
        )
        with self._engine.begin() as connection:
            connection.execute(
                sql,
                {
                    "tenant_id": binding.tenant_id,
                    "provider_ref": binding.provider_ref,
                    "action_id": binding.action_id,
                    "case_id": binding.case_id,
                    "case_revision": binding.case_revision,
                    "updated_at": binding.updated_at,
                },
            )

    def get_binding(self, tenant_id: str, provider_ref: str) -> ProviderBinding | None:
        sql = text(
            f"""
            SELECT * FROM "{self._schema}".provider_bindings
            WHERE tenant_id = :tenant_id AND provider_ref = :provider_ref
            """
        )
        with self._engine.connect() as connection:
            row = (
                connection.execute(sql, {"tenant_id": tenant_id, "provider_ref": provider_ref})
                .mappings()
                .first()
            )
        if row is None:
            return None
        return ProviderBinding(
            tenant_id=row["tenant_id"],
            provider_ref=row["provider_ref"],
            action_id=row["action_id"],
            case_id=row["case_id"],
            case_revision=int(row["case_revision"]),
            updated_at=_ts(row["updated_at"]),
        )


def _inbox_params(record: InboxRecord) -> dict[str, Any]:
    return {
        "tenant_id": record.tenant_id,
        "event_id": record.event_id,
        "provider": record.provider,
        "provider_ref": record.provider_ref,
        "event_type": record.event_type,
        "merchant_ref": record.merchant_ref,
        "occurred_at": record.occurred_at,
        "payload_json": record.payload_json,
        "signature_hex": record.signature_hex,
        "received_at": record.received_at,
        "processed_at": record.processed_at,
        "process_status": record.process_status,
        "reason_code": record.reason_code,
    }


def _recheck_params(job: RecheckJob) -> dict[str, Any]:
    return {
        "tenant_id": job.tenant_id,
        "job_id": job.job_id,
        "idempotency_key": job.idempotency_key,
        "case_id": job.case_id,
        "case_revision": job.case_revision,
        "action_id": job.action_id,
        "provider_ref": job.provider_ref,
        "request_digest": job.request_digest,
        "available_at": job.available_at,
        "lease_expires_at": job.lease_expires_at,
        "attempts": job.attempts,
        "status": job.status,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def _row_to_recheck(row: Any) -> RecheckJob:
    return RecheckJob(
        tenant_id=row["tenant_id"],
        job_id=row["job_id"],
        idempotency_key=row["idempotency_key"],
        case_id=row["case_id"],
        case_revision=int(row["case_revision"]),
        action_id=row["action_id"],
        provider_ref=row["provider_ref"],
        request_digest=row["request_digest"],
        available_at=_ts(row["available_at"]),
        lease_expires_at=_ts(row["lease_expires_at"]) if row["lease_expires_at"] else None,
        attempts=int(row["attempts"]),
        status=row["status"],
        created_at=_ts(row["created_at"]),
        updated_at=_ts(row["updated_at"]),
    )


def _ts(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat().replace("+00:00", "Z")
    return str(value)
