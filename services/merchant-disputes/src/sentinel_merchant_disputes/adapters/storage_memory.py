"""In-memory dispute store for fixture mode and unit tests."""

from __future__ import annotations

from ..application.errors import ConflictError
from ..domain.types import DisputeCase, EvidencePacket


class MemoryDisputeStore:
    def __init__(self) -> None:
        self._disputes: dict[str, DisputeCase] = {}
        self._packets: dict[str, EvidencePacket] = {}
        self._by_idempotency: dict[str, str] = {}
        self._idempotency_payload: dict[str, str] = {}

    def create(self, dispute: DisputeCase, *, idempotency_key: str | None) -> DisputeCase:
        if idempotency_key:
            fingerprint = _fingerprint(dispute)
            existing_id = self._by_idempotency.get(idempotency_key)
            if existing_id is not None:
                if self._idempotency_payload[idempotency_key] != fingerprint:
                    raise ConflictError("Idempotency-Key already used with a different payload")
                return self._disputes[existing_id]
            self._by_idempotency[idempotency_key] = dispute.dispute_id
            self._idempotency_payload[idempotency_key] = fingerprint
        self._disputes[dispute.dispute_id] = dispute
        return dispute

    def get(self, dispute_id: str) -> DisputeCase | None:
        return self._disputes.get(dispute_id)

    def list(self, *, tenant_id: str, merchant_ref: str) -> tuple[DisputeCase, ...]:
        items = [
            dispute
            for dispute in self._disputes.values()
            if dispute.tenant_id == tenant_id and dispute.merchant_ref == merchant_ref
        ]
        return tuple(sorted(items, key=lambda d: d.dispute_id))

    def save(self, dispute: DisputeCase) -> DisputeCase:
        if dispute.dispute_id not in self._disputes:
            raise ConflictError("Unknown dispute")
        self._disputes[dispute.dispute_id] = dispute
        return dispute

    def save_packet(self, packet: EvidencePacket) -> EvidencePacket:
        self._packets[packet.packet_id] = packet
        return packet

    def list_packets(self, dispute_id: str) -> tuple[EvidencePacket, ...]:
        dispute = self._disputes.get(dispute_id)
        if dispute is None:
            return ()
        return tuple(
            self._packets[packet_id]
            for packet_id in dispute.evidence_packet_ids
            if packet_id in self._packets
        )


def _fingerprint(dispute: DisputeCase) -> str:
    return "|".join(
        [
            dispute.tenant_id,
            dispute.merchant_ref,
            dispute.case_id,
            dispute.reason_code,
            dispute.deadline_at,
            dispute.order_reference,
        ]
    )
