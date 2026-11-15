"""Narrow ports consumed by workflow use cases."""

from __future__ import annotations

from typing import Any, Protocol

from sentinel_workflow.domain.types import (
    ActionRecord,
    Approval,
    Case,
    CaseInput,
    CaseResult,
    EvidenceBundle,
    ModelRequest,
    ModelResult,
    PolicyRequest,
    PolicyResult,
    ProposalRequest,
    ReservationRequest,
    VerificationRequest,
    VerificationResult,
)


class CaseApiPort(Protocol):
    def get_input(self, case_id: str, revision: int) -> CaseInput: ...

    def get_case(self, case_id: str) -> Case: ...

    def submit_result(self, case_id: str, result: CaseResult) -> Case: ...


class EvidencePort(Protocol):
    def collect(self, case_id: str, case_revision: int, order_reference: str) -> EvidenceBundle: ...


class PolicyPort(Protocol):
    def evaluate(self, request: PolicyRequest) -> PolicyResult: ...


class LedgerPort(Protocol):
    def create_proposal(self, request: ProposalRequest) -> ActionRecord: ...

    def reserve(self, request: ReservationRequest) -> ActionRecord: ...

    def get_action(self, action_id: str) -> ActionRecord: ...


class VerifierPort(Protocol):
    def schedule_recheck(self, request: VerificationRequest, idempotency_key: str) -> str: ...

    def assess(self, request: VerificationRequest) -> VerificationResult: ...


class ModelPort(Protocol):
    """Structured model adapter. Fake implementations must label themselves."""

    label: str

    def propose(self, request: ModelRequest) -> ModelResult: ...


class JobStorePort(Protocol):
    def accept_job(
        self,
        *,
        tenant_id: str,
        job_key: str,
        payload: dict[str, Any],
        thread_id: str,
    ) -> tuple[str, bool]:
        """Return (job_id, created). Raises on conflicting payload."""

    def get_job(self, tenant_id: str, job_key: str) -> dict[str, Any] | None: ...

    def mark_job_status(self, job_id: str, status: str, detail: str | None = None) -> None: ...

    def claim_failed_job(self, job_id: str) -> bool:
        """Atomically move a `failed` job to `running`; True only for the single winner."""


class OutboxPort(Protocol):
    def enqueue_result(
        self,
        *,
        tenant_id: str,
        case_id: str,
        event_key: str,
        payload: dict[str, Any],
    ) -> None: ...

    def pending(self, limit: int = 50) -> list[dict[str, Any]]: ...

    def mark_delivered(self, outbox_id: str) -> None: ...

    def mark_retry(self, outbox_id: str, error: str) -> None: ...


class DecisionStorePort(Protocol):
    """Stores authenticated resume decisions for approval interrupts."""

    def put_decision(self, thread_id: str, approval: Approval, principal_id: str) -> None: ...

    def get_decision(self, thread_id: str) -> dict[str, Any] | None: ...


class RiskPort(Protocol):
    """Authorized risk hold lookup. Fail closed when the peer is required."""

    def blocks_financial_actions(self, case_id: str) -> bool: ...
