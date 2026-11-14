"""Narrow ports for storage, peers and clock."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from ..domain.types import (
    CaseSnapshot,
    Finding,
    Investigation,
    Principal,
    ResumeEvent,
    RiskRestriction,
)


class Clock(Protocol):
    def now(self) -> datetime: ...


class CaseApiPort(Protocol):
    def get_case(self, case_id: str, *, principal: Principal) -> CaseSnapshot: ...


class WorkflowPort(Protocol):
    """Emit resume/restriction events. Never a financial approval channel."""

    def emit_resume(self, event: ResumeEvent, *, principal: Principal) -> None: ...


class RiskStore(Protocol):
    def create_investigation(
        self,
        investigation: Investigation,
        restriction: RiskRestriction,
        *,
        idempotency_key: str | None,
    ) -> Investigation: ...

    def get_investigation(self, investigation_id: str) -> Investigation | None: ...

    def list_investigations(
        self,
        *,
        tenant_id: str,
        case_id: str | None = None,
    ) -> tuple[Investigation, ...]: ...

    def save_investigation(self, investigation: Investigation) -> Investigation: ...

    def save_finding(self, finding: Finding) -> Finding: ...

    def list_findings(self, investigation_id: str) -> tuple[Finding, ...]: ...

    def get_restriction(self, restriction_id: str) -> RiskRestriction | None: ...

    def save_restriction(self, restriction: RiskRestriction) -> RiskRestriction: ...

    def compare_and_swap_restriction(
        self,
        restriction: RiskRestriction,
        *,
        expected_revision: int,
    ) -> RiskRestriction: ...

    def list_restrictions(
        self,
        *,
        tenant_id: str,
        case_id: str | None = None,
        investigation_id: str | None = None,
    ) -> tuple[RiskRestriction, ...]: ...
