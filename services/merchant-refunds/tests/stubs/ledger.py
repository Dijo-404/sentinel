"""action-ledger.v1 local doubles. Sole mint of action_id."""

from __future__ import annotations

from copy import deepcopy
from typing import Literal

from sentinel_merchant_refunds.domain.errors import PeerError, PeerUnavailableError
from sentinel_merchant_refunds.domain.types import (
    ActionRecord,
    Principal,
    ProposalRequest,
    ReservationRequest,
)

StubMode = Literal["valid", "unavailable", "malformed", "unauthorized_or_out_of_scope"]


class StubLedger:
    def __init__(self, *, mode: StubMode = "valid") -> None:
        self.mode = mode
        self.by_operation: dict[str, ActionRecord] = {}
        self.proposal_calls = 0
        self.reserve_calls = 0
        self._seq = 0

    def create_proposal(self, principal: Principal, request: ProposalRequest) -> ActionRecord:
        del principal
        self._guard()
        if self.mode == "malformed":
            raise PeerError("MALFORMED_PEER", "Malformed ledger response", status_code=502)
        existing = self.by_operation.get(request.operation_key)
        if existing is not None:
            if existing.action_digest != request.action_digest:
                raise PeerError("CONFLICT", "operation_key conflict", status_code=409)
            return deepcopy(existing)
        self.proposal_calls += 1
        self._seq += 1
        record = ActionRecord(
            action_id=f"action-ledger-{self._seq}",
            provider_ref=f"refund-ref-{self._seq}",
            payload=dict(request.payload),
            action_digest=request.action_digest,
            status="PROPOSED",
        )
        self.by_operation[request.operation_key] = record
        return deepcopy(record)

    def reserve(self, principal: Principal, request: ReservationRequest) -> ActionRecord:
        del principal
        self._guard()
        if self.mode == "malformed":
            raise PeerError("MALFORMED_PEER", "Malformed ledger response", status_code=502)
        existing = self.by_operation.get(request.operation_key)
        if existing is None:
            existing = self.create_proposal(
                Principal(
                    principal_id="unused",
                    tenant_id="unused",
                    merchant_ref="unused",
                    roles=["merchant_staff"],
                ),
                ProposalRequest(
                    operation_key=request.operation_key,
                    payload=request.payload,
                    action_digest=request.action_digest,
                ),
            )
        self.reserve_calls += 1
        updated = ActionRecord(
            action_id=existing.action_id,
            provider_ref=existing.provider_ref,
            payload=dict(request.payload),
            action_digest=request.action_digest,
            status="RESERVED",
            approval_id=request.approval_id,
        )
        self.by_operation[request.operation_key] = updated
        return deepcopy(updated)

    def get_action(self, principal: Principal, action_id: str) -> ActionRecord:
        del principal
        self._guard()
        if self.mode == "malformed":
            raise PeerError("MALFORMED_PEER", "Malformed ledger response", status_code=502)
        for record in self.by_operation.values():
            if record.action_id == action_id:
                return deepcopy(record)
        raise PeerError("NOT_FOUND", "Unknown action", status_code=404)

    def set_status(self, action_id: str, status: str) -> None:
        for key, record in self.by_operation.items():
            if record.action_id == action_id:
                self.by_operation[key] = record.model_copy(update={"status": status})
                return
        raise KeyError(action_id)

    def forged_action_ids(self) -> set[str]:
        """IDs minted by this stub only (for assertions)."""
        return {r.action_id for r in self.by_operation.values()}

    def _guard(self) -> None:
        if self.mode == "unavailable":
            raise PeerUnavailableError("action-ledger")
        if self.mode == "unauthorized_or_out_of_scope":
            raise PeerError("FORBIDDEN", "Unauthorized or out of scope", status_code=403)
