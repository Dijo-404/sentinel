"""Real-peer HTTP adapters. Never silently fall back to fixtures."""

from __future__ import annotations

from typing import Any

import httpx

from ..application.errors import (
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from ..domain.types import (
    CaseSnapshot,
    EvidenceBundle,
    EvidenceItem,
    Principal,
)


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class HttpCaseApi:
    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        client: httpx.Client | None = None,
        timeout: float = 10.0,
    ) -> None:
        if not base_url:
            raise PeerUnavailableError("Required peer unavailable: case-api")
        self._base = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout
        self._client = client

    def get_case(self, case_id: str, *, principal: Principal) -> CaseSnapshot:
        del principal
        body = self._request("GET", f"/v1/cases/{case_id}", peer="case-api")
        try:
            return CaseSnapshot(
                contract_version=str(body["contract_version"]),
                case_id=str(body["case_id"]),
                revision=int(body["revision"]),
                status=str(body["status"]),
                language=str(body["language"]),
                intent=str(body["intent"]),
                evidence_ids=tuple(str(x) for x in body.get("evidence_ids", [])),
                order_reference=None,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise PeerMalformedError("case-api returned malformed Case") from exc

    def _request(self, method: str, path: str, *, peer: str) -> dict[str, Any]:
        client = self._client or httpx.Client(timeout=self._timeout)
        owns = self._client is None
        try:
            try:
                response = client.request(
                    method,
                    f"{self._base}{path}",
                    headers=_headers(self._token),
                )
            except httpx.HTTPError as exc:
                raise PeerUnavailableError(f"Required peer unavailable: {peer}") from exc
            return _map_response(response, peer=peer)
        finally:
            if owns:
                client.close()


class HttpEvidence:
    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        client: httpx.Client | None = None,
        timeout: float = 10.0,
    ) -> None:
        if not base_url:
            raise PeerUnavailableError("Required peer unavailable: evidence")
        self._base = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout
        self._client = client

    def collect(
        self,
        *,
        case_id: str,
        case_revision: int,
        order_reference: str,
        principal: Principal,
    ) -> EvidenceBundle:
        del principal
        body = self._request(
            "POST",
            "/v1/evidence/collect",
            peer="evidence",
            json={
                "case_id": case_id,
                "case_revision": case_revision,
                "order_reference": order_reference,
            },
        )
        try:
            evidence = tuple(
                EvidenceItem(
                    evidence_id=str(item["evidence_id"]),
                    case_id=str(item["case_id"]),
                    source=str(item["source"]),
                    subject_ref=str(item["subject_ref"]),
                    observed_at=str(item["observed_at"]),
                    expires_at=str(item["expires_at"]),
                    digest=str(item["digest"]),
                    verification_status=str(item["verification_status"]),
                    facts=dict(item["facts"]),
                )
                for item in body["evidence"]
            )
            return EvidenceBundle(
                contract_version=str(body["contract_version"]),
                case_id=str(body["case_id"]),
                evidence=evidence,
                reconciliation_codes=tuple(str(c) for c in body.get("reconciliation_codes", [])),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise PeerMalformedError("evidence returned malformed EvidenceBundle") from exc

    def _request(
        self,
        method: str,
        path: str,
        *,
        peer: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = self._client or httpx.Client(timeout=self._timeout)
        owns = self._client is None
        try:
            try:
                response = client.request(
                    method,
                    f"{self._base}{path}",
                    headers=_headers(self._token),
                    json=json,
                )
            except httpx.HTTPError as exc:
                raise PeerUnavailableError(f"Required peer unavailable: {peer}") from exc
            return _map_response(response, peer=peer)
        finally:
            if owns:
                client.close()


def _map_response(response: httpx.Response, *, peer: str) -> dict[str, Any]:
    if response.status_code >= 500:
        raise PeerUnavailableError(f"Required peer unavailable: {peer}")
    if response.status_code in {401, 403}:
        raise PeerUnauthorizedError(f"{peer} unauthorized or out of scope")
    if response.status_code >= 400:
        raise PeerMalformedError(f"{peer} returned {response.status_code}")
    try:
        body = response.json()
    except ValueError as exc:
        raise PeerMalformedError(f"{peer} returned non-JSON body") from exc
    if not isinstance(body, dict):
        raise PeerMalformedError(f"{peer} returned non-object JSON")
    return body
