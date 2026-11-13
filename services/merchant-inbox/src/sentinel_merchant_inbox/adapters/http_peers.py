"""Real-peer HTTP adapters. Failures stay visible; no fixture fallback."""

from __future__ import annotations

from typing import Any

import httpx

from sentinel_merchant_inbox.domain.errors import PeerError


class HttpEvidenceClient:
    def __init__(self, base_url: str, *, token: str, timeout: float = 10.0) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def get_case_evidence(self, case_id: str) -> dict[str, Any]:
        response = self._client.get(f"/v1/cases/{case_id}/evidence")
        self._raise(response)
        return response.json()

    def _raise(self, response: httpx.Response) -> None:
        if response.status_code >= 400:
            code, message = _error_fields(response)
            raise PeerError(code, message, status_code=response.status_code)


class HttpCaseApiClient:
    def __init__(self, base_url: str, *, token: str, timeout: float = 10.0) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def get_case(self, case_id: str) -> dict[str, Any]:
        response = self._client.get(f"/v1/cases/{case_id}")
        self._raise(response)
        return response.json()

    def escalate(
        self,
        case_id: str,
        *,
        expected_revision: int,
        reason_code: str,
        owner_queue: str,
    ) -> dict[str, Any]:
        response = self._client.post(
            f"/v1/ops/cases/{case_id}/escalate",
            json={
                "expected_revision": expected_revision,
                "reason_code": reason_code,
                "owner_queue": owner_queue,
            },
        )
        self._raise(response)
        return response.json()

    def _raise(self, response: httpx.Response) -> None:
        if response.status_code >= 400:
            code, message = _error_fields(response)
            raise PeerError(code, message, status_code=response.status_code)


def _error_fields(response: httpx.Response) -> tuple[str, str]:
    try:
        body: Any = response.json()
    except Exception:
        return "PEER_ERROR", response.text or "peer error"
    if isinstance(body, dict):
        return str(body.get("code") or "PEER_ERROR"), str(body.get("message") or "peer error")
    return "PEER_ERROR", "peer error"
