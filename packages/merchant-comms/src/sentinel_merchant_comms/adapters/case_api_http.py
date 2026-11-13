"""Real-peer HTTP adapter for case-api.v1. Failures stay visible; no fixture fallback."""

from __future__ import annotations

from typing import Any

import httpx

from sentinel_merchant_comms.application.errors import (
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_merchant_comms.domain.types import Case, Principal

PEER = "case-api.v1"


class CaseApiHttpClient:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("case-api base_url required for real-peer mode")
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._client = httpx.Client(timeout=timeout, transport=transport)

    def close(self) -> None:
        self._client.close()

    def get_case(self, case_id: str, principal: Principal) -> Case:
        _ = principal  # identity comes from configured bearer, not the body
        url = f"{self._base_url}/v1/cases/{case_id}"
        try:
            response = self._client.get(
                url,
                headers={"Authorization": f"Bearer {self._token}"},
            )
        except httpx.HTTPError as exc:
            raise PeerUnavailableError(PEER, "case-api peer not reachable") from exc

        if response.status_code in {401, 403, 404}:
            raise PeerUnauthorizedError(PEER, "case not in authenticated scope")
        if response.status_code >= 500:
            raise PeerUnavailableError(PEER, f"case-api returned {response.status_code}")
        if response.status_code != 200:
            raise PeerMalformedError(PEER, f"unexpected status {response.status_code}")

        try:
            payload: dict[str, Any] = response.json()
            return Case.model_validate(payload)
        except Exception as exc:
            raise PeerMalformedError(PEER, "response failed Case validation") from exc
