"""Narrow ports for evidence.v1, payment-provider.v1 and finding storage."""

from __future__ import annotations

from typing import Protocol

from sentinel_merchant_settlement.domain.types import (
    PeerWorld,
    Principal,
    SettlementBatch,
    SettlementFinding,
)


class EvidencePort(Protocol):
    """evidence.v1 read surface used during reconciliation."""

    def load_world(
        self,
        *,
        principal: Principal,
        tenant_id: str,
        merchant_ref: str,
        order_refs: tuple[str, ...],
        transaction_refs: tuple[str, ...],
    ) -> PeerWorld: ...


class PaymentProviderPort(Protocol):
    """payment-provider.v1 read surface used during reconciliation."""

    def load_world(
        self,
        *,
        principal: Principal,
        tenant_id: str,
        merchant_ref: str,
        period_start: str,
        period_end: str,
        order_refs: tuple[str, ...],
        transaction_refs: tuple[str, ...],
    ) -> PeerWorld: ...


class FindingStore(Protocol):
    def save_import(self, batch: SettlementBatch, findings: list[SettlementFinding]) -> None: ...

    def get_batch(self, batch_id: str) -> SettlementBatch | None: ...

    def list_findings(
        self, *, batch_id: str | None = None, status: str | None = None
    ) -> list[SettlementFinding]: ...

    def get_finding(self, finding_id: str) -> SettlementFinding | None: ...

    def update_finding(self, finding: SettlementFinding) -> SettlementFinding: ...
