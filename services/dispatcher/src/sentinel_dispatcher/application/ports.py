"""Narrow ports. Ledger remains the only financial authority."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from sentinel_dispatcher.domain.types import (
    Command,
    DispatchJob,
    OutcomeRequest,
    Refund,
    RefundRequest,
)


class Clock(Protocol):
    def now(self) -> datetime: ...


class LedgerPort(Protocol):
    def claim(self, *, limit: int) -> Sequence[Command]: ...

    def report_outcome(self, action_id: str, outcome: OutcomeRequest) -> dict: ...

    def get_action(self, action_id: str) -> dict: ...


class ProviderPort(Protocol):
    def create_refund(self, request: RefundRequest, *, idempotency_key: str) -> Refund: ...

    def get_refund(self, provider_ref: str) -> Refund | None: ...


class WorkerStore(Protocol):
    def save(self, job: DispatchJob) -> None: ...

    def get(self, tenant_id: str, action_id: str) -> DispatchJob | None: ...

    def list_incomplete(self, tenant_id: str) -> Sequence[DispatchJob]: ...
