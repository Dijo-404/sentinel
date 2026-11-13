"""payment-provider.v1 local doubles. Simulated refunds/credits only."""

from __future__ import annotations

from typing import Literal

from sentinel_verifier.domain.errors import PeerError
from sentinel_verifier.domain.types import Credit, Refund

StubMode = Literal["valid", "unavailable", "malformed", "unauthorized_or_out_of_scope"]


class StubProvider:
    def __init__(self, *, mode: StubMode = "valid") -> None:
        self.mode = mode
        self.refunds: dict[str, Refund] = {}
        self.credits: dict[str, Credit] = {}
        self.lookup_calls: list[str] = []
        self.credit_calls: list[str] = []

    def seed_refund(self, refund: Refund) -> None:
        self.refunds[refund.provider_ref] = refund

    def seed_credit(self, credit: Credit) -> None:
        self.credits[credit.provider_ref] = credit

    def get_refund(self, provider_ref: str) -> Refund | None:
        self.lookup_calls.append(provider_ref)
        self._guard()
        return self.refunds.get(provider_ref)

    def get_credit(self, provider_ref: str) -> Credit | None:
        self.credit_calls.append(provider_ref)
        self._guard()
        return self.credits.get(provider_ref)

    def _guard(self) -> None:
        if self.mode == "unavailable":
            raise PeerError("PEER_UNAVAILABLE", "Required peer unavailable", status_code=503)
        if self.mode == "malformed":
            raise PeerError("MALFORMED_PEER", "Malformed provider response", status_code=502)
        if self.mode == "unauthorized_or_out_of_scope":
            raise PeerError("FORBIDDEN", "Unauthorized or out of scope", status_code=403)
