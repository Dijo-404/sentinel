"""Local evidence.v1 doubles. Never imported from services/evidence."""

from __future__ import annotations

from dataclasses import dataclass, field

from sentinel_merchant_settlement.application.errors import (
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_merchant_settlement.domain.types import EvidenceRecord, PeerWorld, Principal

CASE_VALID = "valid"
CASE_UNAVAILABLE = "unavailable"
CASE_MALFORMED = "malformed"
CASE_UNAUTHORIZED = "unauthorized_or_out_of_scope"


def demo_evidence() -> tuple[EvidenceRecord, ...]:
    return (
        EvidenceRecord("evidence-txn-ok", "TXN-OK", "ORDER-OK", "VERIFIED"),
        EvidenceRecord("evidence-txn-fee", "TXN-FEE", "ORDER-FEE", "VERIFIED"),
        EvidenceRecord("evidence-txn-short", "TXN-SHORT", "ORDER-SHORT", "VERIFIED"),
        EvidenceRecord("evidence-txn-miss", "TXN-MISS-SETTLE", "ORDER-MISS-SETTLE", "VERIFIED"),
        EvidenceRecord("evidence-txn-dup", "TXN-DUP", "ORDER-DUP", "VERIFIED"),
        EvidenceRecord("evidence-txn-unmatched", "TXN-UNMATCHED", "ORDER-REAL", "VERIFIED"),
        EvidenceRecord("evidence-ghost", "TXN-GHOST", None, "UNVERIFIED"),
    )


@dataclass
class StubEvidence:
    case: str = CASE_VALID
    evidence: tuple[EvidenceRecord, ...] = field(default_factory=demo_evidence)

    def load_world(
        self,
        *,
        principal: Principal,
        tenant_id: str,
        merchant_ref: str,
        order_refs: tuple[str, ...],
        transaction_refs: tuple[str, ...],
    ) -> PeerWorld:
        del order_refs, transaction_refs, merchant_ref
        if self.case == CASE_UNAVAILABLE:
            raise PeerUnavailableError("Required peer unavailable")
        if self.case == CASE_MALFORMED:
            raise PeerMalformedError("Evidence response failed schema validation")
        if self.case == CASE_UNAUTHORIZED:
            raise PeerUnauthorizedError("Evidence denied scoped read")
        if principal.tenant_id != tenant_id:
            raise PeerUnauthorizedError("Evidence denied scoped read")
        return PeerWorld(payments=(), orders=(), evidence=self.evidence)
