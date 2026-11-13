"""payment-provider.v1 local doubles. Simulated refunds only."""

from __future__ import annotations

from typing import Any, Literal

from sentinel_dispatcher.domain.types import PeerError, ProviderTimeout, Refund, RefundRequest

StubMode = Literal[
    "valid",
    "unavailable",
    "malformed",
    "unauthorized_or_out_of_scope",
    "commit_then_timeout",
    "timeout_before_commit",
    "ambiguous_not_found",
]


class StubProvider:
    def __init__(self, *, mode: StubMode = "valid") -> None:
        self.mode = mode
        self.refunds: dict[str, Refund] = {}
        self.side_effects: list[str] = []
        self.create_calls: list[dict[str, Any]] = []
        self.lookup_calls: list[str] = []

    def side_effect_count(self, provider_ref: str | None = None) -> int:
        if provider_ref is None:
            return len(self.side_effects)
        return sum(1 for item in self.side_effects if item == provider_ref)

    def create_refund(self, request: RefundRequest, *, idempotency_key: str) -> Refund:
        self.create_calls.append({"request": request.as_dict(), "idempotency_key": idempotency_key})
        if idempotency_key != request.provider_ref:
            raise PeerError(
                "REFERENCE_MISMATCH",
                "Idempotency-Key must equal provider_ref",
                status_code=422,
            )
        if self.mode == "unavailable":
            raise PeerError("PEER_UNAVAILABLE", "Required peer unavailable", status_code=503)
        if self.mode == "malformed":
            raise PeerError("MALFORMED_PEER", "Malformed provider response", status_code=502)
        if self.mode == "unauthorized_or_out_of_scope":
            raise PeerError("FORBIDDEN", "Unauthorized or out of scope", status_code=403)
        if self.mode == "timeout_before_commit":
            raise ProviderTimeout("Timed out before provider commit")

        existing = self.refunds.get(request.provider_ref)
        if existing is not None:
            # Idempotent replay under the same stable reference.
            if (
                existing.action_id != request.action_id
                or existing.transaction_ref != request.transaction_ref
                or existing.amount_minor != request.amount_minor
            ):
                raise PeerError(
                    "IDEMPOTENCY_CONFLICT",
                    "Key already used with a different payload",
                    status_code=409,
                )
            if self.mode == "commit_then_timeout":
                raise ProviderTimeout("Timed out after idempotent replay")
            return existing

        refund = Refund(
            action_id=request.action_id,
            provider_ref=request.provider_ref,
            transaction_ref=request.transaction_ref,
            amount_minor=request.amount_minor,
            currency=request.currency,
            status="PENDING",
        )
        self.refunds[request.provider_ref] = refund
        self.side_effects.append(request.provider_ref)
        if self.mode == "commit_then_timeout":
            raise ProviderTimeout("Timed out after provider accepted refund")
        return refund

    def get_refund(self, provider_ref: str) -> Refund | None:
        self.lookup_calls.append(provider_ref)
        if self.mode == "unavailable":
            raise PeerError("PEER_UNAVAILABLE", "Required peer unavailable", status_code=503)
        if self.mode == "malformed":
            raise PeerError("MALFORMED_PEER", "Malformed provider response", status_code=502)
        if self.mode == "unauthorized_or_out_of_scope":
            raise PeerError("FORBIDDEN", "Unauthorized or out of scope", status_code=403)
        if self.mode == "ambiguous_not_found":
            raise PeerError(
                "NOT_FOUND",
                "Reference not currently visible; outcome remains unknown",
                status_code=404,
            )
        return self.refunds.get(provider_ref)
