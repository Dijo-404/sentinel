"""Narrow ports consumed by merchant analytics use cases."""

from __future__ import annotations

from typing import Protocol

from ..domain.types import CaseRecord, Principal, RefundFact


class CaseApiPort(Protocol):
    def list_merchant_cases(
        self,
        principal: Principal,
        *,
        merchant_ref: str,
        window_start: str,
        window_end: str,
    ) -> list[CaseRecord]:
        """Return merchant-scoped cases opened inside the window. Read-only."""


class EvidencePort(Protocol):
    def list_refund_facts(
        self,
        principal: Principal,
        *,
        case_ids: list[str],
    ) -> list[RefundFact]:
        """Return refund facts for the given cases. Read-only."""
