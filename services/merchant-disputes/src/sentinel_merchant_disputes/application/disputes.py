"""Use cases: create, collect packet, submit, resolve, deadline view."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import timedelta

from ..domain import lifecycle
from ..domain.types import (
    CreateDisputeRequest,
    DeadlineView,
    DisputeCase,
    EvidencePacket,
    Principal,
    TerminalStatus,
)
from . import errors
from .ports import CaseApiPort, Clock, DisputeStore, EvidencePort


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class DisputeService:
    def __init__(
        self,
        *,
        case_api: CaseApiPort,
        evidence: EvidencePort,
        store: DisputeStore,
        clock: Clock,
        default_deadline_seconds: int = 604800,
    ) -> None:
        self._case_api = case_api
        self._evidence = evidence
        self._store = store
        self._clock = clock
        self._default_deadline_seconds = default_deadline_seconds

    def create(
        self,
        principal: Principal,
        request: CreateDisputeRequest,
        *,
        idempotency_key: str | None = None,
    ) -> DisputeCase:
        self._authorize(
            principal,
            tenant_id=principal.tenant_id,
            case_id=request.case_id,
            merchant_ref=request.merchant_ref,
        )
        case = self._case_api.get_case(request.case_id, principal=principal)
        if case.case_id != request.case_id:
            raise errors.PeerMalformedError("case-api returned mismatched case_id")
        order_reference = request.order_reference or case.order_reference or ""
        if not order_reference:
            raise errors.ValidationError("order_reference is required")
        if not request.reason_code.strip():
            raise errors.ValidationError("reason_code is required")
        now = self._clock.now()
        if request.deadline_at:
            try:
                lifecycle.parse_rfc3339(request.deadline_at)
            except ValueError as exc:
                raise errors.ValidationError("deadline_at must be RFC 3339 UTC") from exc
            deadline_at = request.deadline_at
            if not deadline_at.endswith("Z"):
                raise errors.ValidationError("deadline_at must use Z suffix")
        else:
            deadline_at = lifecycle.format_rfc3339(
                now + timedelta(seconds=self._default_deadline_seconds)
            )
        dispute = DisputeCase(
            dispute_id=_new_id("dispute"),
            tenant_id=principal.tenant_id,
            merchant_ref=request.merchant_ref,
            case_id=request.case_id,
            reason_code=request.reason_code,
            deadline_at=deadline_at,
            evidence_packet_ids=(),
            status="OPEN",
            order_reference=order_reference,
            case_revision=case.revision,
        )
        return self._store.create(dispute, idempotency_key=idempotency_key)

    def get(self, principal: Principal, dispute_id: str) -> DisputeCase:
        dispute = self._require(dispute_id)
        self._authorize(
            principal,
            tenant_id=dispute.tenant_id,
            case_id=dispute.case_id,
            merchant_ref=dispute.merchant_ref,
        )
        return dispute

    def collect_packet(self, principal: Principal, dispute_id: str) -> DisputeCase:
        dispute = self._require(dispute_id)
        self._authorize(
            principal,
            tenant_id=dispute.tenant_id,
            case_id=dispute.case_id,
            merchant_ref=dispute.merchant_ref,
        )
        try:
            lifecycle.assert_can_collect(dispute)
        except ValueError as exc:
            raise errors.ConflictError(str(exc)) from exc
        bundle = self._evidence.collect(
            case_id=dispute.case_id,
            case_revision=dispute.case_revision,
            order_reference=dispute.order_reference,
            principal=principal,
        )
        if bundle.case_id != dispute.case_id:
            raise errors.PeerMalformedError("evidence returned mismatched case_id")
        kinds = tuple(sorted({item.kind for item in bundle.evidence if item.kind is not None}))
        packet = EvidencePacket(
            packet_id=_new_id("packet"),
            dispute_id=dispute.dispute_id,
            case_id=dispute.case_id,
            evidence_ids=tuple(item.evidence_id for item in bundle.evidence),
            kinds=kinds,
            assembled_at=lifecycle.format_rfc3339(self._clock.now()),
        )
        self._store.save_packet(packet)
        updated = replace(
            dispute,
            evidence_packet_ids=(*dispute.evidence_packet_ids, packet.packet_id),
            status=lifecycle.after_packet_collected(dispute),
        )
        return self._store.save(updated)

    def submit(self, principal: Principal, dispute_id: str) -> DisputeCase:
        dispute = self._require(dispute_id)
        self._authorize(
            principal,
            tenant_id=dispute.tenant_id,
            case_id=dispute.case_id,
            merchant_ref=dispute.merchant_ref,
        )
        packets = self._store.list_packets(dispute_id)
        try:
            lifecycle.assert_can_submit(dispute, packets, now=self._clock.now())
        except lifecycle.MissingEvidenceError as exc:
            raise errors.MissingEvidenceError(exc.missing) from exc
        except lifecycle.DeadlineError as exc:
            raise errors.DeadlinePassedError(str(exc)) from exc
        except ValueError as exc:
            raise errors.ConflictError(str(exc)) from exc
        return self._store.save(replace(dispute, status="SUBMITTED"))

    def resolve(
        self,
        principal: Principal,
        dispute_id: str,
        outcome: TerminalStatus,
    ) -> DisputeCase:
        if outcome not in {"WON", "LOST", "WITHDRAWN"}:
            raise errors.ValidationError("outcome must be WON, LOST, or WITHDRAWN")
        dispute = self._require(dispute_id)
        self._authorize(
            principal,
            tenant_id=dispute.tenant_id,
            case_id=dispute.case_id,
            merchant_ref=dispute.merchant_ref,
        )
        try:
            lifecycle.assert_can_resolve(dispute, outcome)
        except ValueError as exc:
            raise errors.ConflictError(str(exc)) from exc
        return self._store.save(replace(dispute, status=outcome))

    def deadline(self, principal: Principal, dispute_id: str) -> DeadlineView:
        dispute = self.get(principal, dispute_id)
        return DeadlineView(
            dispute_id=dispute.dispute_id,
            deadline_at=dispute.deadline_at,
            overdue=lifecycle.is_overdue(deadline_at=dispute.deadline_at, now=self._clock.now()),
            status=dispute.status,
        )

    def _require(self, dispute_id: str) -> DisputeCase:
        dispute = self._store.get(dispute_id)
        if dispute is None:
            raise errors.NotFoundError("Dispute not found")
        return dispute

    def _authorize(
        self,
        principal: Principal,
        *,
        tenant_id: str,
        case_id: str,
        merchant_ref: str,
    ) -> None:
        if not principal.is_operator():
            raise errors.UnauthorizedError("Operator or supervisor role required")
        # Uniform deny for unauthorized scope — do not leak existence.
        if (
            principal.tenant_id != tenant_id
            or not principal.allows_case(case_id)
            or not principal.allows_merchant(merchant_ref)
        ):
            raise errors.UnauthorizedError("Unauthorized or out of scope")
