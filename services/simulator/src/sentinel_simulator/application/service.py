from __future__ import annotations

from sentinel_simulator.domain.models import (
    Credit,
    FaultSchedule,
    Order,
    Payment,
    Principal,
    ProviderEvent,
    Refund,
    RefundRequest,
    RefundStats,
)
from sentinel_simulator.domain.rules import (
    IdempotencyConflict,
    NotFound,
    TimeoutAfterAccept,
    Unauthorized,
    Unavailable,
    ValidationError,
    refund_fingerprint,
)

from .ports import Store

READ_ROLES = frozenset({"workflow", "verifier", "sandbox-admin"})
REFUND_LOOKUP_ROLES = frozenset({"dispatcher", "verifier", "workflow"})
CREDIT_ROLES = frozenset({"verifier", "workflow"})
DISPATCHER_ROLES = frozenset({"dispatcher"})
ADMIN_ROLES = frozenset({"sandbox-admin"})


class PaymentSimulator:
    def __init__(self, store: Store) -> None:
        self._store = store

    def delay_ms(self) -> int:
        return self._store.faults().delay_ms

    def require_roles(self, principal: Principal, allowed: frozenset[str]) -> None:
        if not allowed.intersection(principal.roles):
            raise Unauthorized("role not permitted for this route")

    def require_subject(self, principal: Principal, subject_ref: str) -> None:
        if subject_ref not in principal.subject_refs and "sandbox-admin" not in principal.roles:
            raise Unauthorized("subject not in principal scope")

    def _check_outage(self) -> None:
        if self._store.faults().outage:
            raise Unavailable("Provider outage")

    def list_transactions(self, principal: Principal, order_reference: str) -> list[Payment]:
        self.require_roles(principal, READ_ROLES)
        self._check_outage()
        order = self._store.get_order(order_reference)
        if order is None:
            raise NotFound("order not found")
        self.require_subject(principal, order.subject_ref)
        return self._store.list_payments(order_reference)

    def get_order(self, principal: Principal, order_reference: str) -> Order:
        self.require_roles(principal, READ_ROLES)
        self._check_outage()
        order = self._store.get_order(order_reference)
        if order is None:
            raise NotFound("order not found")
        self.require_subject(principal, order.subject_ref)
        return order

    def list_refunds(self, principal: Principal, transaction_ref: str) -> list[Refund]:
        self.require_roles(principal, READ_ROLES)
        self._check_outage()
        payment = self._store.get_payment(transaction_ref)
        if payment is None:
            raise NotFound("transaction not found")
        self.require_subject(principal, payment.subject_ref)
        return self._store.list_refunds(transaction_ref)

    def get_refund(self, principal: Principal, provider_ref: str) -> Refund:
        self.require_roles(principal, REFUND_LOOKUP_ROLES)
        self._check_outage()
        refund = self._store.get_refund(provider_ref)
        if refund is None:
            raise NotFound("refund not found")
        payment = self._store.get_payment(refund.transaction_ref)
        if payment is not None:
            self.require_subject(principal, payment.subject_ref)
        return refund

    def get_credit(self, principal: Principal, provider_ref: str) -> Credit:
        self.require_roles(principal, CREDIT_ROLES)
        self._check_outage()
        credit = self._store.get_credit(provider_ref)
        if credit is None:
            raise NotFound("credit not found")
        return credit

    def create_refund(self, principal: Principal, request: RefundRequest) -> Refund:
        self.require_roles(principal, DISPATCHER_ROLES)
        self._check_outage()
        payment = self._store.get_payment(request.transaction_ref)
        if payment is None:
            raise NotFound("transaction not found")
        self.require_subject(principal, payment.subject_ref)
        if payment.status != "CAPTURED":
            raise ValidationError("refund requires a CAPTURED payment")
        if request.amount_minor > payment.amount_minor:
            raise ValidationError("refund amount exceeds captured payment")
        if request.currency != payment.currency:
            raise ValidationError("refund currency must match payment")

        fingerprint = refund_fingerprint(request)
        existing = self._store.get_refund(request.provider_ref)
        stats = self._store.get_stats(request.provider_ref)
        if existing is not None:
            if stats.fingerprint and stats.fingerprint != fingerprint:
                raise IdempotencyConflict()
            # Identical retry: no new side effect.
            stats.accept_count += 1
            self._store.put_stats(stats)
            if self._store.faults().timeout_after_accept:
                stats.timeout_count += 1
                self._store.put_stats(stats)
                raise TimeoutAfterAccept(request.provider_ref)
            return existing

        refund = Refund(
            action_id=request.action_id,
            provider_ref=request.provider_ref,
            transaction_ref=request.transaction_ref,
            amount_minor=request.amount_minor,
            currency="INR",
            status="PENDING",
        )
        self._store.put_refund(refund)
        stats = RefundStats(
            provider_ref=request.provider_ref,
            accept_count=1,
            side_effect_count=1,
            timeout_count=0,
            fingerprint=fingerprint,
        )
        self._store.put_stats(stats)
        if self._store.faults().timeout_after_accept:
            stats.timeout_count = 1
            self._store.put_stats(stats)
            raise TimeoutAfterAccept(request.provider_ref)
        return refund

    def get_faults(self, principal: Principal) -> FaultSchedule:
        self.require_roles(principal, ADMIN_ROLES)
        return self._store.faults()

    def set_faults(self, principal: Principal, payload: dict) -> FaultSchedule:
        self.require_roles(principal, ADMIN_ROLES)
        faults = self._store.faults()
        if "outage" in payload:
            if not isinstance(payload["outage"], bool):
                raise ValidationError("outage must be bool")
            faults.outage = payload["outage"]
        if "delay_ms" in payload:
            delay = payload["delay_ms"]
            if not isinstance(delay, int) or isinstance(delay, bool) or delay < 0:
                raise ValidationError("delay_ms must be a non-negative int")
            faults.delay_ms = delay
        if "timeout_after_accept" in payload:
            if not isinstance(payload["timeout_after_accept"], bool):
                raise ValidationError("timeout_after_accept must be bool")
            faults.timeout_after_accept = payload["timeout_after_accept"]
        if "duplicate_events" in payload:
            if not isinstance(payload["duplicate_events"], bool):
                raise ValidationError("duplicate_events must be bool")
            faults.duplicate_events = payload["duplicate_events"]
        if "out_of_order_credit" in payload:
            if not isinstance(payload["out_of_order_credit"], bool):
                raise ValidationError("out_of_order_credit must be bool")
            faults.out_of_order_credit = payload["out_of_order_credit"]
        return faults

    def reset_faults(self, principal: Principal) -> FaultSchedule:
        self.require_roles(principal, ADMIN_ROLES)
        faults = self._store.faults()
        faults.reset()
        return faults

    def refund_stats(self, principal: Principal, provider_ref: str) -> RefundStats:
        self.require_roles(principal, ADMIN_ROLES)
        return self._store.get_stats(provider_ref)

    def confirm_refund(self, principal: Principal, provider_ref: str) -> Refund:
        """Mark provider outcome PROVIDER_CONFIRMED. Does not create credit."""
        self.require_roles(principal, ADMIN_ROLES)
        refund = self._store.get_refund(provider_ref)
        if refund is None:
            raise NotFound("refund not found")
        if refund.status == "FAILED_FINAL":
            raise ValidationError("cannot confirm a FAILED_FINAL refund")
        confirmed = Refund(
            action_id=refund.action_id,
            provider_ref=refund.provider_ref,
            transaction_ref=refund.transaction_ref,
            amount_minor=refund.amount_minor,
            currency=refund.currency,
            status="PROVIDER_CONFIRMED",
        )
        self._store.put_refund(confirmed)
        self._emit_confirmation_events(principal.tenant_id, confirmed)
        return confirmed

    def confirm_credit(self, principal: Principal, provider_ref: str) -> Credit:
        """Separate customer-credit evidence; not implied by provider confirmation."""
        self.require_roles(principal, ADMIN_ROLES)
        refund = self._store.get_refund(provider_ref)
        if refund is None:
            raise NotFound("refund not found")
        if refund.status != "PROVIDER_CONFIRMED":
            raise ValidationError("credit requires PROVIDER_CONFIRMED refund")
        existing = self._store.get_credit(provider_ref)
        if existing is not None and existing.confirmed:
            return existing
        credit = Credit(
            provider_ref=provider_ref,
            confirmed=True,
            observed_at=self._store.clock().now(),
        )
        self._store.put_credit(credit)
        self._store.append_event(
            ProviderEvent(
                event_id=self._store.clock().next_event_id("evt-credit"),
                tenant_id=principal.tenant_id,
                merchant_ref="demo-merchant",
                provider_ref=provider_ref,
                type="CREDIT_STATUS",
                occurred_at=self._store.clock().now(),
                payload_status="CONFIRMED",
            )
        )
        return credit

    def list_events(self, principal: Principal) -> list[ProviderEvent]:
        self.require_roles(principal, ADMIN_ROLES)
        return self._store.list_events()

    def _emit_confirmation_events(self, tenant_id: str, refund: Refund) -> None:
        faults = self._store.faults()
        clock = self._store.clock()
        refund_event = ProviderEvent(
            event_id=clock.next_event_id("evt-refund"),
            tenant_id=tenant_id,
            merchant_ref="demo-merchant",
            provider_ref=refund.provider_ref,
            type="REFUND_STATUS",
            occurred_at=clock.now(),
            payload_status="PROVIDER_CONFIRMED",
        )
        if faults.out_of_order_credit:
            # Credit-looking event before refund confirmation; credit record still absent.
            self._store.append_event(
                ProviderEvent(
                    event_id=clock.next_event_id("evt-credit-early"),
                    tenant_id=tenant_id,
                    merchant_ref="demo-merchant",
                    provider_ref=refund.provider_ref,
                    type="CREDIT_STATUS",
                    occurred_at=clock.now(),
                    payload_status="CLAIMED_UNCONFIRMED",
                )
            )
        self._store.append_event(refund_event)
        if faults.duplicate_events:
            self._store.append_event(
                ProviderEvent(
                    event_id=clock.next_event_id("evt-refund-dup"),
                    tenant_id=tenant_id,
                    merchant_ref="demo-merchant",
                    provider_ref=refund.provider_ref,
                    type="REFUND_STATUS",
                    occurred_at=clock.now(),
                    payload_status="PROVIDER_CONFIRMED",
                )
            )
