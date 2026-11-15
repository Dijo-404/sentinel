from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

PaymentStatus = Literal["CAPTURED", "PENDING", "FAILED"]
RefundStatus = Literal["PENDING", "PROVIDER_CONFIRMED", "FAILED_FINAL"]
Currency = Literal["INR"]
Destination = Literal["ORIGINAL_PAYMENT_ROUTE"]


@dataclass(frozen=True)
class Principal:
    principal_id: str
    tenant_id: str
    roles: tuple[str, ...]
    subject_refs: tuple[str, ...]
    case_ids: tuple[str, ...]


@dataclass(frozen=True)
class Payment:
    transaction_ref: str
    order_reference: str
    subject_ref: str
    status: PaymentStatus
    amount_minor: int
    currency: Currency
    merchant_ref: str = "merchant-demo-1"

    def to_dict(self) -> dict:
        return {
            "transaction_ref": self.transaction_ref,
            "order_reference": self.order_reference,
            "subject_ref": self.subject_ref,
            "status": self.status,
            "amount_minor": self.amount_minor,
            "currency": self.currency,
            "merchant_ref": self.merchant_ref,
        }


@dataclass(frozen=True)
class Order:
    order_reference: str
    subject_ref: str
    fulfilled_order_count: int
    merchant_confirmed_duplicate: bool
    paid: bool

    def to_dict(self) -> dict:
        return {
            "order_reference": self.order_reference,
            "subject_ref": self.subject_ref,
            "fulfilled_order_count": self.fulfilled_order_count,
            "merchant_confirmed_duplicate": self.merchant_confirmed_duplicate,
            "paid": self.paid,
        }


@dataclass(frozen=True)
class RefundRequest:
    action_id: str
    provider_ref: str
    transaction_ref: str
    amount_minor: int
    currency: Currency
    destination: Destination

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "provider_ref": self.provider_ref,
            "transaction_ref": self.transaction_ref,
            "amount_minor": self.amount_minor,
            "currency": self.currency,
            "destination": self.destination,
        }


@dataclass(frozen=True)
class Refund:
    action_id: str
    provider_ref: str
    transaction_ref: str
    amount_minor: int
    currency: Currency
    status: RefundStatus

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "provider_ref": self.provider_ref,
            "transaction_ref": self.transaction_ref,
            "amount_minor": self.amount_minor,
            "currency": self.currency,
            "status": self.status,
        }


@dataclass(frozen=True)
class Credit:
    provider_ref: str
    confirmed: bool
    observed_at: str

    def to_dict(self) -> dict:
        return {
            "provider_ref": self.provider_ref,
            "confirmed": self.confirmed,
            "observed_at": self.observed_at,
        }


@dataclass(frozen=True)
class ProviderEvent:
    event_id: str
    tenant_id: str
    merchant_ref: str
    provider_ref: str
    type: Literal["REFUND_STATUS", "CREDIT_STATUS"]
    occurred_at: str
    payload_status: str

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "tenant_id": self.tenant_id,
            "merchant_ref": self.merchant_ref,
            "provider_ref": self.provider_ref,
            "type": self.type,
            "occurred_at": self.occurred_at,
            "payload_status": self.payload_status,
        }


@dataclass
class FaultSchedule:
    outage: bool = False
    delay_ms: int = 0
    timeout_after_accept: bool = False
    duplicate_events: bool = False
    out_of_order_credit: bool = False

    def to_dict(self) -> dict:
        return {
            "outage": self.outage,
            "delay_ms": self.delay_ms,
            "timeout_after_accept": self.timeout_after_accept,
            "duplicate_events": self.duplicate_events,
            "out_of_order_credit": self.out_of_order_credit,
        }

    def reset(self) -> None:
        self.outage = False
        self.delay_ms = 0
        self.timeout_after_accept = False
        self.duplicate_events = False
        self.out_of_order_credit = False


@dataclass
class RefundStats:
    provider_ref: str
    accept_count: int = 0
    side_effect_count: int = 0
    timeout_count: int = 0
    fingerprint: str = ""

    def to_dict(self) -> dict:
        return {
            "provider_ref": self.provider_ref,
            "accept_count": self.accept_count,
            "side_effect_count": self.side_effect_count,
            "timeout_count": self.timeout_count,
        }


@dataclass
class SimulatorClock:
    """Injectable clock; default starts at fixed demo instant."""

    instant: str = "2026-11-13T12:00:00Z"
    _seq: int = field(default=0, repr=False)

    def now(self) -> str:
        return self.instant

    def next_event_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}-{self._seq}"
