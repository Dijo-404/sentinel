"""Real-peer HTTP adapters. Failures stay visible; no fixture fallback."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

from sentinel_dispatcher.domain.types import (
    Command,
    OutcomeRequest,
    PeerError,
    ProviderTimeout,
    Refund,
    RefundRequest,
)


class HttpLedgerClient:
    def __init__(self, base_url: str, *, token: str, timeout: float = 10.0) -> None:
        self._base = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def claim(self, *, limit: int) -> Sequence[Command]:
        response = self._client.post("/v1/actions/claims", json={"limit": limit})
        self._raise_for_status(response)
        body = response.json()
        return [Command.from_mapping(item) for item in body.get("commands", [])]

    def report_outcome(self, action_id: str, outcome: OutcomeRequest) -> dict:
        response = self._client.post(
            f"/v1/actions/{action_id}/outcomes",
            json=outcome.as_dict(),
        )
        self._raise_for_status(response)
        return response.json()

    def get_action(self, action_id: str) -> dict:
        response = self._client.get(f"/v1/actions/{action_id}")
        self._raise_for_status(response)
        return response.json()

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code >= 400:
            code, message = _error_fields(response)
            raise PeerError(code, message, status_code=response.status_code)


class HttpProviderClient:
    def __init__(self, base_url: str, *, token: str, timeout: float = 10.0) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def create_refund(self, request: RefundRequest, *, idempotency_key: str) -> Refund:
        if idempotency_key != request.provider_ref:
            raise PeerError(
                "REFERENCE_MISMATCH",
                "Idempotency-Key must equal provider_ref",
                status_code=422,
            )
        try:
            response = self._client.post(
                "/v1/refunds",
                json=request.as_dict(),
                headers={"Idempotency-Key": idempotency_key},
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeout() from exc
        if response.status_code >= 400:
            code, message = _error_fields(response)
            raise PeerError(code, message, status_code=response.status_code)
        return Refund.from_mapping(response.json())

    def get_refund(self, provider_ref: str) -> Refund | None:
        response = self._client.get(f"/v1/refunds/{provider_ref}")
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            code, message = _error_fields(response)
            raise PeerError(code, message, status_code=response.status_code)
        return Refund.from_mapping(response.json())


def _error_fields(response: httpx.Response) -> tuple[str, str]:
    try:
        body: Any = response.json()
        return str(body.get("code", "PEER_ERROR")), str(body.get("message", response.text))
    except Exception:
        return "PEER_ERROR", response.text or "peer request failed"
