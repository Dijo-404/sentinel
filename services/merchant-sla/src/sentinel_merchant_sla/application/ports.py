"""Narrow ports for clock, storage, and case-api.v1."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from sentinel_merchant_sla.contracts import CaseRecord, Principal, SlaPolicy, SlaTask


class Clock(Protocol):
    def now(self) -> datetime: ...


class SlaStore(Protocol):
    def put_policy(self, policy: SlaPolicy) -> SlaPolicy: ...

    def get_policy(self, policy_id: str) -> SlaPolicy | None: ...

    def list_policies(self, *, tenant_id: str, merchant_ref: str) -> list[SlaPolicy]: ...

    def put_task(self, task: SlaTask) -> SlaTask: ...

    def get_task(self, task_id: str) -> SlaTask | None: ...

    def list_tasks(
        self,
        *,
        tenant_id: str,
        merchant_ref: str | None = None,
        case_id: str | None = None,
    ) -> list[SlaTask]: ...

    def next_id(self, prefix: str) -> str: ...


class CaseApiPort(Protocol):
    def get_case(self, case_id: str, principal: Principal) -> CaseRecord: ...

    def escalate_case(
        self,
        case_id: str,
        *,
        expected_revision: int,
        reason_code: str,
        owner_queue: str,
        principal: Principal,
    ) -> CaseRecord: ...
