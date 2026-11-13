"""Real-peer HTTP adapters. Failures stay visible; no fixture fallback."""

from __future__ import annotations

from typing import Any

import httpx

from sentinel_verifier.domain.errors import PeerError
from sentinel_verifier.domain.types import Credit, OutcomeRequest, Refund


class HttpProviderClient:
    def __init__(self, base_url: str, *, token: str, timeout: float = 10.0) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def get_refund(self, provider_ref: str) -> Refund | None:
        response = self._client.get(f"/v1/refunds/{provider_ref}")
        if response.status_code == 404:
            return None
        self._raise(response)
        return Refund.from_mapping(response.json())

    def get_credit(self, provider_ref: str) -> Credit | None:
        response = self._client.get(f"/v1/credits/{provider_ref}")
        if response.status_code == 404:
            return None
        self._raise(response)
        return Credit.from_mapping(response.json())

    def _raise(self, response: httpx.Response) -> None:
        if response.status_code >= 400:
            code, message = _error_fields(response)
            raise PeerError(code, message, status_code=response.status_code)


class HttpLedgerClient:
    def __init__(self, base_url: str, *, token: str, timeout: float = 10.0) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def get_action(self, action_id: str) -> dict[str, Any]:
        response = self._client.get(f"/v1/actions/{action_id}")
        self._raise(response)
        return response.json()

    def report_outcome(self, action_id: str, outcome: OutcomeRequest) -> dict[str, Any]:
        response = self._client.post(
            f"/v1/actions/{action_id}/outcomes",
            json=outcome.as_dict(),
        )
        self._raise(response)
        return response.json()

    def _raise(self, response: httpx.Response) -> None:
        if response.status_code >= 400:
            code, message = _error_fields(response)
            raise PeerError(code, message, status_code=response.status_code)


class HttpEvidenceClient:
    def __init__(self, base_url: str, *, token: str, timeout: float = 10.0) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def collect(self, *, case_id: str, case_revision: int, order_reference: str) -> dict[str, Any]:
        response = self._client.post(
            "/v1/evidence/collect",
            json={
                "case_id": case_id,
                "case_revision": case_revision,
                "order_reference": order_reference,
            },
        )
        self._raise(response)
        return response.json()

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

    def submit_result(self, case_id: str, result: dict[str, Any]) -> dict[str, Any]:
        response = self._client.post(f"/v1/internal/cases/{case_id}/results", json=result)
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
