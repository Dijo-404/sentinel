"""Narrow ports for payment-provider reads, evidence storage and clock."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from ..domain.types import CollectRequest, EvidenceBundle, Principal, ProviderSnapshot


class Clock(Protocol):
    def now(self) -> datetime: ...


class PaymentProviderPort(Protocol):
    """payment-provider.v1 read surface used by evidence collection."""

    def fetch_snapshot(self, *, order_reference: str, principal: Principal) -> ProviderSnapshot: ...


class EvidenceStore(Protocol):
    def save_bundle(
        self,
        *,
        principal: Principal,
        request: CollectRequest,
        bundle: EvidenceBundle,
    ) -> EvidenceBundle: ...

    def get_bundle(self, *, principal: Principal, case_id: str) -> EvidenceBundle | None: ...
