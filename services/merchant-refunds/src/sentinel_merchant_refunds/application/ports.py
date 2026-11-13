"""Narrow ports consumed by merchant refund use cases."""

from __future__ import annotations

from typing import Protocol

from sentinel_merchant_refunds.domain.types import (
    ActionRecord,
    CaseRecord,
    EvidenceBundle,
    MerchantRefundRequest,
    PolicyResult,
    Principal,
    ProposalRequest,
    ReservationRequest,
)


class Clock(Protocol):
    def now_iso(self) -> str: ...


class IdGenerator(Protocol):
    def new_id(self, prefix: str) -> str: ...


class RequestStore(Protocol):
    def put(self, request: MerchantRefundRequest) -> None: ...

    def get(self, tenant_id: str, request_id: str) -> MerchantRefundRequest | None: ...

    def get_by_idempotency(
        self, tenant_id: str, idempotency_key: str
    ) -> MerchantRefundRequest | None: ...

    def put_idempotency(
        self, tenant_id: str, idempotency_key: str, request: MerchantRefundRequest
    ) -> None: ...


class CaseApiPort(Protocol):
    def get_case(self, principal: Principal, case_id: str) -> CaseRecord: ...


class EvidencePort(Protocol):
    def get_case_evidence(self, principal: Principal, case_id: str) -> EvidenceBundle: ...


class PolicyPort(Protocol):
    def evaluate(
        self,
        principal: Principal,
        *,
        payload: dict,
        evidence_ids: list[str],
        approval: dict | None = None,
    ) -> PolicyResult: ...


class LedgerPort(Protocol):
    def create_proposal(self, principal: Principal, request: ProposalRequest) -> ActionRecord: ...

    def reserve(self, principal: Principal, request: ReservationRequest) -> ActionRecord: ...

    def get_action(self, principal: Principal, action_id: str) -> ActionRecord: ...
