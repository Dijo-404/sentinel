"""Narrow ports injected into use cases."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from sentinel_api.domain.types import (
    Approval,
    Case,
    CaseCreate,
    CaseCreated,
    CaseEvent,
    CaseInput,
    CaseResult,
    DecisionRequest,
    EvidenceBundle,
    Principal,
    VerificationResult,
    WorkflowRequest,
)


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new_id(self, prefix: str) -> str: ...


class CaseRepository(Protocol):
    def create_case(
        self,
        *,
        principal: Principal,
        create: CaseCreate,
        idempotency_key: str,
        case_id: str,
        message_id: str,
        event_id: str,
        occurred_at: str,
    ) -> tuple[CaseCreated, Case, bool]:
        """Return (created, case, reused). Raises DomainError on conflict."""
        ...

    def get_case(self, *, tenant_id: str, case_id: str) -> Case | None: ...

    def get_case_meta(self, *, tenant_id: str, case_id: str) -> dict | None:
        """Internal metadata: subject_ref, order_reference, original_text, status filter fields."""
        ...

    def add_message(
        self,
        *,
        principal: Principal,
        case_id: str,
        message: str,
        language: str,
        expected_revision: int,
        message_id: str,
        event_id: str,
        author: str,
        occurred_at: str,
    ) -> Case: ...

    def list_events(
        self, *, tenant_id: str, case_id: str, after_sequence: int
    ) -> list[CaseEvent]: ...

    def list_queue(
        self, *, tenant_id: str, status: str | None, after: str | None, limit: int
    ) -> tuple[list[Case], str | None]: ...

    def escalate(
        self,
        *,
        principal: Principal,
        case_id: str,
        expected_revision: int,
        reason_code: str,
        owner_queue: str,
        event_id: str,
        occurred_at: str,
    ) -> Case: ...

    def claim_case(
        self,
        *,
        principal: Principal,
        case_id: str,
        event_id: str,
        occurred_at: str,
    ) -> Case:
        """Atomic assignment. Raises DomainError CONFLICT (409) if owned by another."""
        ...

    def list_case_rows(
        self,
        *,
        tenant_id: str,
        subject_refs: tuple[str, ...] | None = None,
    ) -> list[dict]:
        """Case rows for dashboard/list projections (tenant-scoped; optional subject filter)."""
        ...

    def get_input(self, *, tenant_id: str, case_id: str, revision: int) -> CaseInput | None: ...

    def apply_result(
        self,
        *,
        principal: Principal,
        case_id: str,
        result: CaseResult,
        event_id: str,
        occurred_at: str,
        assessment_ref: str | None,
    ) -> Case: ...

    def enqueue_workflow(self, *, tenant_id: str, request: WorkflowRequest) -> None: ...

    def claim_workflow_jobs(self, *, limit: int = 20) -> list[tuple[str, WorkflowRequest]]: ...

    def mark_workflow_job(self, *, job_row_id: str, status: str, detail: str = "") -> None: ...

    def ping(self) -> None: ...


class WorkflowPort(Protocol):
    def start_run(self, request: WorkflowRequest, *, authorization: str) -> None: ...


class EvidencePort(Protocol):
    def get_case_evidence(self, case_id: str, *, authorization: str) -> EvidenceBundle: ...


class LedgerPort(Protocol):
    def decide(
        self, action_id: str, request: DecisionRequest, *, authorization: str
    ) -> Approval: ...


class VerifierPort(Protocol):
    def get_assessment(self, assessment_id: str, *, authorization: str) -> VerificationResult: ...
