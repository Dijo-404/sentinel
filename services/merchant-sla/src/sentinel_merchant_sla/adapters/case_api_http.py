"""Real-peer HTTP adapter for case-api.v1. Fail closed; no fixture fallback."""

from __future__ import annotations

from typing import Any

import httpx

from sentinel_merchant_sla.application.errors import (
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_merchant_sla.contracts import CaseRecord, Principal, SlaInputError, parse_case


class HttpCaseApi:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.Client | None = None,
    ) -> None:
        if not base_url or not token:
            raise PeerUnavailableError("case-api")
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._client = client or httpx.Client(timeout=10.0)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def get_case(self, case_id: str, principal: Principal) -> CaseRecord:
        del principal
        return self._request("GET", f"/v1/cases/{case_id}")

    def escalate_case(
        self,
        case_id: str,
        *,
        expected_revision: int,
        reason_code: str,
        owner_queue: str,
        principal: Principal,
    ) -> CaseRecord:
        del principal
        return self._request(
            "POST",
            f"/v1/ops/cases/{case_id}/escalate",
            json={
                "expected_revision": expected_revision,
                "reason_code": reason_code,
                "owner_queue": owner_queue,
            },
        )

    def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> CaseRecord:
        url = f"{self._base_url}{path}"
        headers = {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}
        try:
            response = self._client.request(method, url, headers=headers, json=json)
        except httpx.HTTPError as exc:
            raise PeerUnavailableError("case-api") from exc
        if response.status_code in {401, 403, 404}:
            raise PeerUnauthorizedError("peer unauthorized or out of scope")
        if response.status_code >= 500:
            raise PeerUnavailableError("case-api")
        if response.status_code >= 400:
            raise PeerMalformedError(f"unexpected peer status {response.status_code}")
        try:
            body = response.json()
        except ValueError as exc:
            raise PeerMalformedError("peer returned non-JSON body") from exc
        try:
            return parse_case(body)
        except SlaInputError as exc:
            raise PeerMalformedError(exc.message) from exc
