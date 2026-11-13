from __future__ import annotations

from dataclasses import dataclass


class PeerUnavailable(RuntimeError):
    def __init__(self, peer: str, request_id: str = "replay-real-peer") -> None:
        self.peer = peer
        self.payload = {
            "code": "PEER_UNAVAILABLE",
            "message": f"Required peer unavailable: {peer}",
            "request_id": request_id,
        }
        super().__init__(self.payload["message"])


@dataclass(frozen=True)
class RealPeerConfig:
    evaluation_url: str | None = None
    payment_provider_url: str | None = None

    @property
    def evaluation_configured(self) -> bool:
        return bool(self.evaluation_url)

    @property
    def payment_provider_configured(self) -> bool:
        return bool(self.payment_provider_url)


class RealEvaluationAdapter:
    """Real evaluation.v1 adapter. Absent URL fails closed; never falls back to fixtures."""

    def __init__(self, base_url: str | None) -> None:
        self.base_url = base_url

    def capabilities(self) -> dict:
        if not self.base_url:
            raise PeerUnavailable("evaluation.v1")
        raise PeerUnavailable("evaluation.v1")  # no live peer in this module

    def score_suite(self, report_payload: dict) -> dict:
        del report_payload
        if not self.base_url:
            raise PeerUnavailable("evaluation.v1")
        raise PeerUnavailable("evaluation.v1")


class RealPaymentProviderAdapter:
    """Real payment-provider.v1 adapter. Absent URL fails closed; never mints refunds."""

    def __init__(self, base_url: str | None) -> None:
        self.base_url = base_url

    def capabilities(self) -> dict:
        if not self.base_url:
            raise PeerUnavailable("payment-provider.v1")
        raise PeerUnavailable("payment-provider.v1")

    def get_transactions(self, order_reference: str) -> dict:
        del order_reference
        if not self.base_url:
            raise PeerUnavailable("payment-provider.v1")
        raise PeerUnavailable("payment-provider.v1")

    def create_refund(self, body: dict, idempotency_key: str) -> dict:
        del body, idempotency_key
        if not self.base_url:
            raise PeerUnavailable("payment-provider.v1")
        raise PeerUnavailable("payment-provider.v1")
