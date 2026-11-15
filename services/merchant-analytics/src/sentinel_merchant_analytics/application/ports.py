"""Narrow ports consumed by merchant analytics use cases."""

from __future__ import annotations

from typing import Protocol

from ..domain.types import CaseRecord, MerchantMetrics, Principal, RefundFact


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


class MetricsSnapshotStore(Protocol):
    def get(
        self,
        *,
        tenant_id: str,
        merchant_ref: str,
        window_start: str,
        window_end: str,
    ) -> MerchantMetrics | None:
        """Return a persisted metrics snapshot or None when absent."""

    def latest(
        self,
        *,
        tenant_id: str,
        merchant_ref: str,
    ) -> MerchantMetrics | None:
        """Return the newest snapshot for merchant, or None when absent."""

    def put(self, metrics: MerchantMetrics) -> None:
        """Upsert a metrics snapshot row."""
