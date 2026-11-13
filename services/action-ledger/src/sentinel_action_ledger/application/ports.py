"""Narrow ports injected into use cases."""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from sentinel_action_ledger.domain.money import PaymentBalance
from sentinel_action_ledger.domain.types import (
    ActionRecord,
    Approval,
    Command,
    EligibilitySnapshot,
    Principal,
)


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new_id(self, prefix: str) -> str: ...


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    evidence_id: str
    case_id: str
    source: str
    subject_ref: str
    observed_at: str
    expires_at: str
    digest: str
    verification_status: str
    facts: dict[str, Any]


class EvidencePort(Protocol):
    def collect(
        self, *, principal: Principal, case_id: str, case_revision: int, order_reference: str
    ) -> Sequence[EvidenceItem]: ...


class PolicyPort(Protocol):
    def evaluate(
        self,
        *,
        principal: Principal,
        payload: dict[str, Any],
        evidence: Sequence[EvidenceItem],
        approval: Approval | None = None,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class StoredAction:
    tenant_id: str
    action_id: str
    operation_key: str
    provider_ref: str
    payload: dict[str, Any]
    action_digest: str
    status: str
    amount_minor: int
    currency: str
    transaction_ref: str
    case_id: str
    case_revision: int
    policy_version: str
    approval_id: str | None
    lease_id: str | None
    lease_expires_at: str | None
    created_at: str
    updated_at: str


class LedgerStore(Protocol):
    def transaction(self) -> AbstractContextManager[LedgerUnitOfWork]: ...


class LedgerUnitOfWork(Protocol):
    def get_action_by_id(self, tenant_id: str, action_id: str) -> StoredAction | None: ...

    def get_action_by_operation_key(
        self, tenant_id: str, operation_key: str
    ) -> StoredAction | None: ...

    def insert_action(self, action: StoredAction) -> None: ...

    def update_action(self, action: StoredAction) -> None: ...

    def insert_approval(
        self, *, tenant_id: str, action_id: str, approval: Approval, created_at: str
    ) -> None: ...

    def get_approval(self, tenant_id: str, approval_id: str) -> Approval | None: ...

    def get_approval_for_action(self, tenant_id: str, action_id: str) -> Approval | None: ...

    def lock_payment(self, tenant_id: str, transaction_ref: str) -> PaymentBalance | None: ...

    def upsert_payment(
        self,
        *,
        tenant_id: str,
        transaction_ref: str,
        merchant_ref: str,
        captured_minor: int,
        currency: str,
    ) -> None: ...

    def write_payment_balance(
        self, tenant_id: str, transaction_ref: str, balance: PaymentBalance
    ) -> None: ...

    def get_eligibility(
        self, tenant_id: str, transaction_ref: str
    ) -> EligibilitySnapshot | None: ...

    def upsert_eligibility(self, snapshot: EligibilitySnapshot) -> None: ...

    def insert_outbox(
        self,
        *,
        tenant_id: str,
        action_id: str,
        available_at: str,
        payload: dict[str, Any],
    ) -> None: ...

    def claim_outbox(
        self,
        *,
        tenant_id: str,
        limit: int,
        lease_id: str,
        lease_expires_at: str,
        now: str,
    ) -> list[Command]: ...

    def insert_audit(
        self,
        *,
        tenant_id: str,
        action_id: str,
        event_type: str,
        actor_id: str,
        detail: dict[str, Any],
        occurred_at: str,
    ) -> None: ...

    def record_outcome_event(
        self,
        *,
        tenant_id: str,
        action_id: str,
        event_key: str,
        status: str,
        reason_code: str,
        evidence_ids: Sequence[str],
        occurred_at: str,
    ) -> bool:
        """Return True if inserted; False if identical retry."""
        ...

    def to_record(self, action: StoredAction) -> ActionRecord: ...


class NetworkProbe(Protocol):
    def begin_guard(self) -> AbstractContextManager[None]: ...

    def assert_idle(self) -> None:
        """Raise if a network call is attempted inside a reservation transaction."""
        ...
