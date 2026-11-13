"""In-memory store for non-durable unit tests only."""

from __future__ import annotations

import json

from sentinel_verifier.domain.types import (
    InboxRecord,
    ProviderBinding,
    RecheckJob,
    VerificationResult,
)


class MemoryVerifierStore:
    def __init__(self) -> None:
        self.inbox: dict[tuple[str, str], InboxRecord] = {}
        self.rechecks: dict[tuple[str, str], RecheckJob] = {}
        self.rechecks_by_key: dict[tuple[str, str], str] = {}
        self.assessments: dict[tuple[str, str], VerificationResult] = {}
        self.bindings: dict[tuple[str, str], ProviderBinding] = {}

    def insert_inbox(self, record: InboxRecord) -> InboxRecord:
        key = (record.tenant_id, record.event_id)
        existing = self.inbox.get(key)
        if existing is not None:
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
        self.inbox[key] = record
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
        return self.inbox.get((tenant_id, event_id))

    def mark_inbox_processed(
        self,
        tenant_id: str,
        event_id: str,
        *,
        process_status: str,
        reason_code: str | None,
        processed_at: str,
    ) -> None:
        key = (tenant_id, event_id)
        current = self.inbox[key]
        self.inbox[key] = InboxRecord(
            tenant_id=current.tenant_id,
            event_id=current.event_id,
            provider=current.provider,
            provider_ref=current.provider_ref,
            event_type=current.event_type,
            merchant_ref=current.merchant_ref,
            occurred_at=current.occurred_at,
            payload_json=current.payload_json,
            signature_hex=current.signature_hex,
            received_at=current.received_at,
            processed_at=processed_at,
            process_status=process_status,
            reason_code=reason_code,
        )

    def save_recheck(self, job: RecheckJob) -> RecheckJob:
        self.rechecks[(job.tenant_id, job.job_id)] = job
        self.rechecks_by_key[(job.tenant_id, job.idempotency_key)] = job.job_id
        return job

    def get_recheck_by_idempotency(self, tenant_id: str, idempotency_key: str) -> RecheckJob | None:
        job_id = self.rechecks_by_key.get((tenant_id, idempotency_key))
        if job_id is None:
            return None
        return self.rechecks.get((tenant_id, job_id))

    def get_recheck(self, tenant_id: str, job_id: str) -> RecheckJob | None:
        return self.rechecks.get((tenant_id, job_id))

    def save_assessment(self, result: VerificationResult, *, tenant_id: str) -> None:
        self.assessments[(tenant_id, result.assessment_id)] = result

    def get_assessment(self, tenant_id: str, assessment_id: str) -> VerificationResult | None:
        return self.assessments.get((tenant_id, assessment_id))

    def save_binding(self, binding: ProviderBinding) -> None:
        self.bindings[(binding.tenant_id, binding.provider_ref)] = binding

    def get_binding(self, tenant_id: str, provider_ref: str) -> ProviderBinding | None:
        return self.bindings.get((tenant_id, provider_ref))

    def dump_inbox(self) -> list[dict]:
        return [json.loads(json.dumps(r.__dict__)) for r in self.inbox.values()]
