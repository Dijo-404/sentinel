"""Real-peer identity.v1 membership HTTP adapter. Fail closed; never fixture fallback."""

from __future__ import annotations

import json
from typing import Any

import httpx

from ..application.errors import (
    ConfigurationError,
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from ..domain.types import CONTRACT_VERSION, IdentityMembership, Principal


class HttpIdentityMemberships:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.Client | None = None,
    ):
        if not base_url.strip():
            raise ConfigurationError("IDENTITY_BASE_URL is required when identity peer is enabled")
        if not token.strip():
            raise ConfigurationError("IDENTITY_TOKEN is required when identity peer is enabled")
        self._base = base_url.rstrip("/")
        self._token = token
        self._client = client or httpx.Client(timeout=10.0)

    def list_memberships(
        self,
        *,
        tenant_id: str,
        merchant_ref: str,
        principal: Principal,
    ) -> tuple[IdentityMembership, ...]:
        del principal  # peer authorizes via bearer; client role headers are never trusted
        try:
            response = self._client.get(
                f"{self._base}/v1/merchant-memberships",
                params={"tenant_id": tenant_id, "merchant_ref": merchant_ref},
                headers={"Authorization": f"Bearer {self._token}"},
            )
        except httpx.HTTPError as exc:
            raise PeerUnavailableError("Required peer unavailable") from exc

        if response.status_code in {401, 403}:
            raise PeerUnauthorizedError("identity denied membership read")
        if response.status_code >= 500:
            raise PeerUnavailableError("Required peer unavailable")
        if response.status_code != 200:
            raise PeerMalformedError("identity returned unexpected status")

        raw = response.content
        try:
            body: Any = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PeerMalformedError("identity response was not valid JSON") from exc

        try:
            if not isinstance(body, dict):
                raise TypeError("object required")
            if body.get("contract_version") != CONTRACT_VERSION:
                raise ValueError("incompatible contract_version")
            rows = body.get("memberships")
            if not isinstance(rows, list):
                raise TypeError("memberships must be a list")
            return tuple(IdentityMembership.from_wire(row) for row in rows)
        except (KeyError, TypeError, ValueError) as exc:
            raise PeerMalformedError("identity response failed schema validation") from exc
