from __future__ import annotations

from dataclasses import dataclass, field

from sentinel_replay.adapters.production_guard import ProductionGuard
from sentinel_replay.domain.models import SideEffect

SANDBOX_REFUND_ROUTE = "sandbox://payment-provider/v1/refunds"


@dataclass
class _RefundRow:
    action_id: str
    provider_ref: str
    transaction_ref: str
    amount_minor: int
    currency: str
    destination: str
    status: str = "PENDING"
    credit_confirmed: bool = False


@dataclass
class SandboxSimulator:
    """In-process simulated payment world for counterfactual replay only."""

    guard: ProductionGuard = field(default_factory=ProductionGuard)
    timeout_after_accept: bool = True
    _seed: int = 0
    _refunds: dict[str, _RefundRow] = field(default_factory=dict)
    _effects: list[SideEffect] = field(default_factory=list)
    _accept_counts: dict[str, int] = field(default_factory=dict)

    def reset(self, *, seed: int) -> None:
        self._seed = seed
        self._refunds.clear()
        self._effects.clear()
        self._accept_counts.clear()
        self.timeout_after_accept = True

    def request_refund(
        self,
        *,
        provider_ref: str,
        action_id: str,
        transaction_ref: str,
        amount_minor: int,
        currency: str = "INR",
        destination: str = "ORIGINAL_PAYMENT_ROUTE",
    ) -> dict:
        self.guard.check_write(SANDBOX_REFUND_ROUTE)
        existing = self._refunds.get(provider_ref)
        if existing is not None:
            self._accept_counts[provider_ref] = self._accept_counts.get(provider_ref, 0) + 1
            body = self._row_dict(existing)
            if self.timeout_after_accept:
                return {"code": "TIMEOUT_AFTER_ACCEPT", "refund": body}
            return body

        row = _RefundRow(
            action_id=action_id,
            provider_ref=provider_ref,
            transaction_ref=transaction_ref,
            amount_minor=amount_minor,
            currency=currency,
            destination=destination,
        )
        self._refunds[provider_ref] = row
        self._accept_counts[provider_ref] = 1
        self._effects.append(
            SideEffect(
                kind="REFUND_WRITE",
                provider_ref=provider_ref,
                transaction_ref=transaction_ref,
                amount_minor=amount_minor,
                route=SANDBOX_REFUND_ROUTE,
            )
        )
        body = self._row_dict(row)
        if self.timeout_after_accept:
            return {"code": "TIMEOUT_AFTER_ACCEPT", "refund": body}
        return body

    def lookup_refund(self, provider_ref: str) -> dict | None:
        row = self._refunds.get(provider_ref)
        if row is None:
            return None
        return self._row_dict(row)

    def confirm_provider(self, provider_ref: str) -> dict:
        row = self._refunds[provider_ref]
        row.status = "PROVIDER_CONFIRMED"
        return self._row_dict(row)

    def confirm_credit(self, provider_ref: str) -> dict:
        row = self._refunds[provider_ref]
        row.credit_confirmed = True
        return {
            "provider_ref": provider_ref,
            "confirmed": True,
            "observed_at": "2026-11-13T12:00:00Z",
        }

    def side_effects(self) -> tuple[SideEffect, ...]:
        return tuple(self._effects)

    def refund_side_effect_count(self) -> int:
        return len(self._effects)

    def attempt_production_write(self, route: str) -> None:
        self.guard.check_write(route)

    def attempt_production_notification(self, route: str) -> None:
        self.guard.check_notification(route)

    @staticmethod
    def _row_dict(row: _RefundRow) -> dict:
        return {
            "action_id": row.action_id,
            "provider_ref": row.provider_ref,
            "transaction_ref": row.transaction_ref,
            "amount_minor": row.amount_minor,
            "currency": row.currency,
            "status": row.status,
        }
