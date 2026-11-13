"""Real-peer case-api.v1 HTTP adapter. Fail closed; never fall back to fixtures."""

from __future__ import annotations

import json
from typing import Any

import httpx

from ..application.errors import (
    ConfigurationError,
    NotFoundError,
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from ..domain.types import CONTRACT_VERSION, CaseSnapshot, Principal


class HttpCaseApi:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.Client | None = None,
    ):
        if not base_url.strip():
            raise ConfigurationError("CASE_API_BASE_URL is required in real-peers mode")
        if not token.strip():
            raise ConfigurationError("CASE_API_TOKEN is required in real-peers mode")
        self._base = base_url.rstrip("/")
        self._token = token
        self._client = client or httpx.Client(timeout=10.0)

    def get_case(self, case_id: str, *, principal: Principal) -> CaseSnapshot:
        del principal  # peer authorizes via bearer; identity headers are never trusted
        try:
            response = self._client.get(
                f"{self._base}/v1/cases/{case_id}",
                headers={"Authorization": f"Bearer {self._token}"},
            )
        except httpx.HTTPError as exc:
            raise PeerUnavailableError("Required peer unavailable") from exc

        if response.status_code in {401, 403}:
            raise PeerUnauthorizedError("case-api denied scoped read")
        if response.status_code == 404:
            raise NotFoundError("Unknown case")
        if response.status_code >= 500:
            raise PeerUnavailableError("Required peer unavailable")
        if response.status_code != 200:
            raise PeerMalformedError("case-api returned unexpected status")

        raw = response.content
        try:
            body: Any = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PeerMalformedError("case-api response was not valid JSON") from exc

        try:
            if not isinstance(body, dict):
                raise TypeError("object required")
            if body.get("contract_version") != CONTRACT_VERSION:
                raise ValueError("incompatible contract_version")
            return CaseSnapshot(
                case_id=str(body["case_id"]),
                revision=int(body["revision"]),
                status=str(body["status"]),
                contract_version=str(body["contract_version"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise PeerMalformedError("case-api response failed schema validation") from exc
