"""Local payment-provider.v1 doubles. Never imported from services/simulator."""

from __future__ import annotations

from dataclasses import dataclass

from ..application.errors import PeerMalformedError, PeerUnauthorizedError, PeerUnavailableError
from ..domain.digest import canonical_json_bytes
from ..domain.types import Order, Payment, Principal, ProviderSnapshot, Refund

CASE = "valid"
STALE = "stale"
CONFLICTING = "conflicting"
EQUAL_ONLY = "equal_amounts_only"
UNAVAILABLE = "unavailable"
MALFORMED = "malformed"
UNAUTHORIZED = "unauthorized_or_out_of_scope"


@dataclass
class StubPaymentProvider:
    """Deterministic fixture provider selected by order_reference suffix/case key."""

    case: str = CASE
    observed_at: str = "2026-11-13T12:00:00Z"
    expires_at: str = "2026-11-13T13:00:00Z"

    def fetch_snapshot(self, *, order_reference: str, principal: Principal) -> ProviderSnapshot:
        del principal
        key = self.case
        # Fixture scenario marker is ``#`` (not ``:``/``/``) so it never collides
        # with authorized subject-boundary forms handled by provider_order_id.
        bare = order_reference.split("#", 1)[0]
        if order_reference.endswith("#stale") or key == STALE:
            return self._valid(
                order_reference=bare,
                expires_at="2026-11-13T11:00:00Z",
                merchant_confirmed=True,
                fulfilled=1,
            )
        if order_reference.endswith("#conflict") or key == CONFLICTING:
            return self._conflicting(bare)
        if order_reference.endswith("#equal") or key == EQUAL_ONLY:
            return self._valid(
                order_reference=bare,
                merchant_confirmed=False,
                fulfilled=2,
            )
        if order_reference.endswith("#unavailable") or key == UNAVAILABLE:
            raise PeerUnavailableError("Required peer unavailable")
        if order_reference.endswith("#malformed") or key == MALFORMED:
            raise PeerMalformedError("Provider response failed schema validation")
        if order_reference.endswith("#unauthorized") or key == UNAUTHORIZED:
            raise PeerUnauthorizedError("Provider denied scoped read")
        return self._valid(
            order_reference=bare,
            merchant_confirmed=True,
            fulfilled=1,
        )

    def _valid(
        self,
        *,
        order_reference: str,
        merchant_confirmed: bool,
        fulfilled: int,
        expires_at: str | None = None,
    ) -> ProviderSnapshot:
        payments = (
            Payment(
                "TXN-A",
                order_reference,
                "subj-demo-1",
                "CAPTURED",
                150000,
                "INR",
                "merchant-demo-1",
            ),
            Payment(
                "TXN-B",
                order_reference,
                "subj-demo-1",
                "CAPTURED",
                150000,
                "INR",
                "merchant-demo-1",
            ),
        )
        order = Order(order_reference, "subj-demo-1", fulfilled, merchant_confirmed, True)
        refund = Refund(
            "action-demo-1",
            "refund-demo-1",
            "TXN-B",
            150000,
            "INR",
            "PENDING",
        )
        payment_items = tuple((canonical_json_bytes(_payment_dict(p)), p) for p in payments)
        return ProviderSnapshot(
            payment_items=payment_items,
            order_payload=canonical_json_bytes(_order_dict(order)),
            order=order,
            refund_items=((canonical_json_bytes(_refund_dict(refund)), refund),),
            observed_at=self.observed_at,
            expires_at=expires_at or self.expires_at,
        )

    def _conflicting(self, order_reference: str) -> ProviderSnapshot:
        # Same transaction_ref with contradictory amounts → CONFLICTING.
        payments = (
            Payment(
                "TXN-A",
                order_reference,
                "subj-demo-1",
                "CAPTURED",
                150000,
                "INR",
                "merchant-demo-1",
            ),
            Payment(
                "TXN-A",
                order_reference,
                "subj-demo-1",
                "CAPTURED",
                99900,
                "INR",
                "merchant-demo-1",
            ),
        )
        order = Order(order_reference, "subj-demo-1", 1, False, True)
        payment_items = tuple((canonical_json_bytes(_payment_dict(p)), p) for p in payments)
        return ProviderSnapshot(
            payment_items=payment_items,
            order_payload=canonical_json_bytes(_order_dict(order)),
            order=order,
            refund_items=(),
            observed_at=self.observed_at,
            expires_at=self.expires_at,
        )


def _payment_dict(payment: Payment) -> dict:
    return {
        "transaction_ref": payment.transaction_ref,
        "order_reference": payment.order_reference,
        "subject_ref": payment.subject_ref,
        "status": payment.status,
        "amount_minor": payment.amount_minor,
        "currency": payment.currency,
        "merchant_ref": payment.merchant_ref,
    }


def _order_dict(order: Order) -> dict:
    return {
        "order_reference": order.order_reference,
        "subject_ref": order.subject_ref,
        "fulfilled_order_count": order.fulfilled_order_count,
        "merchant_confirmed_duplicate": order.merchant_confirmed_duplicate,
        "paid": order.paid,
    }


def _refund_dict(refund: Refund) -> dict:
    return {
        "action_id": refund.action_id,
        "provider_ref": refund.provider_ref,
        "transaction_ref": refund.transaction_ref,
        "amount_minor": refund.amount_minor,
        "currency": refund.currency,
        "status": refund.status,
    }


class CaseSelectingStub:
    """Routes order_reference case suffixes to distinct stub behaviors."""

    def fetch_snapshot(self, *, order_reference: str, principal: Principal) -> ProviderSnapshot:
        return StubPaymentProvider().fetch_snapshot(
            order_reference=order_reference, principal=principal
        )
