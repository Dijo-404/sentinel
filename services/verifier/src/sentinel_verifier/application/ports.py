"""Narrow ports. Ledger remains the only financial authority."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from sentinel_verifier.domain.types import (
    Credit,
    InboxRecord,
    OutcomeRequest,
    ProviderBinding,
    RecheckJob,
    Refund,
    VerificationResult,
)


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new_id(self, prefix: str) -> str: ...


class ProviderPort(Protocol):
    def get_refund(self, provider_ref: str) -> Refund | None: ...

    def get_credit(self, provider_ref: str) -> Credit | None: ...


class LedgerPort(Protocol):
    def get_action(self, action_id: str) -> dict[str, Any]: ...

    def report_outcome(self, action_id: str, outcome: OutcomeRequest) -> dict[str, Any]: ...


class EvidencePort(Protocol):
    def collect(
        self, *, case_id: str, case_revision: int, order_reference: str
    ) -> dict[str, Any]: ...

    def get_case_evidence(self, case_id: str) -> dict[str, Any]: ...


class CaseApiPort(Protocol):
    def get_case(self, case_id: str) -> dict[str, Any]: ...

    def submit_result(self, case_id: str, result: dict[str, Any]) -> dict[str, Any]: ...


class VerifierStore(Protocol):
    def insert_inbox(self, record: InboxRecord) -> InboxRecord: ...

    def get_inbox(self, tenant_id: str, event_id: str) -> InboxRecord | None: ...

    def mark_inbox_processed(
        self,
        tenant_id: str,
        event_id: str,
        *,
        process_status: str,
        reason_code: str | None,
        processed_at: str,
    ) -> None: ...

    def save_recheck(self, job: RecheckJob) -> RecheckJob: ...

    def get_recheck_by_idempotency(
        self, tenant_id: str, idempotency_key: str
    ) -> RecheckJob | None: ...

    def get_recheck(self, tenant_id: str, job_id: str) -> RecheckJob | None: ...

    def save_assessment(self, result: VerificationResult, *, tenant_id: str) -> None: ...

    def get_assessment(self, tenant_id: str, assessment_id: str) -> VerificationResult | None: ...

    def save_binding(self, binding: ProviderBinding) -> None: ...

    def get_binding(self, tenant_id: str, provider_ref: str) -> ProviderBinding | None: ...
