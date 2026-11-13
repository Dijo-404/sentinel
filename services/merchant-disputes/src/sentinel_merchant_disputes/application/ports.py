"""Narrow ports for case-api, evidence, storage and clock."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from ..domain.types import (
    CaseSnapshot,
    DisputeCase,
    EvidenceBundle,
    EvidencePacket,
    Principal,
)


class Clock(Protocol):
    def now(self) -> datetime: ...


class CaseApiPort(Protocol):
    """case-api.v1 read surface used when opening a dispute."""

    def get_case(self, case_id: str, *, principal: Principal) -> CaseSnapshot: ...


class EvidencePort(Protocol):
    """evidence.v1 collect surface used when assembling packets."""

    def collect(
        self,
        *,
        case_id: str,
        case_revision: int,
        order_reference: str,
        principal: Principal,
    ) -> EvidenceBundle: ...


class DisputeStore(Protocol):
    def create(self, dispute: DisputeCase, *, idempotency_key: str | None) -> DisputeCase: ...

    def get(self, dispute_id: str) -> DisputeCase | None: ...

    def save(self, dispute: DisputeCase) -> DisputeCase: ...

    def save_packet(self, packet: EvidencePacket) -> EvidencePacket: ...

    def list_packets(self, dispute_id: str) -> tuple[EvidencePacket, ...]: ...
