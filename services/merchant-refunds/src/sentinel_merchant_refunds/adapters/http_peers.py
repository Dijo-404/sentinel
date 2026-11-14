"""Real-peer HTTP adapters. Failures stay visible; no fixture fallback."""

from __future__ import annotations

from typing import Any

import httpx

from sentinel_merchant_refunds.domain.errors import PeerError, PeerUnavailableError
from sentinel_merchant_refunds.domain.types import (
    ActionRecord,
    CaseRecord,
    EvidenceBundle,
    PolicyResult,
    Principal,
    ProposalRequest,
    ReservationRequest,
)


def _error_fields(response: httpx.Response) -> tuple[str, str]:
    try:
        body = response.json()
        code = str(body.get("code") or "PEER_ERROR")
        message = str(body.get("message") or response.text)
    except Exception:
        code, message = "PEER_ERROR", response.text or "peer error"
    return code, message


class HttpCaseApiClient:
    def __init__(self, base_url: str, *, token: str, timeout: float = 10.0) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def get_case(self, principal: Principal, case_id: str) -> CaseRecord:
        del principal
        try:
            response = self._client.get(f"/v1/cases/{case_id}")
        except httpx.HTTPError as exc:
            raise PeerUnavailableError("case-api") from exc
        self._raise(response)
        return CaseRecord.model_validate(response.json())

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

    def get_case_evidence(self, principal: Principal, case_id: str) -> EvidenceBundle:
        del principal
        try:
            response = self._client.get(f"/v1/cases/{case_id}/evidence")
        except httpx.HTTPError as exc:
            raise PeerUnavailableError("evidence") from exc
        self._raise(response)
        return EvidenceBundle.model_validate(response.json())

    def _raise(self, response: httpx.Response) -> None:
        if response.status_code >= 400:
            code, message = _error_fields(response)
            raise PeerError(code, message, status_code=response.status_code)


class HttpPolicyClient:
    def __init__(self, base_url: str, *, token: str, timeout: float = 10.0) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def evaluate(
        self,
        principal: Principal,
        *,
        payload: dict[str, Any],
        evidence: list[dict[str, Any]],
        approval: dict[str, Any] | None = None,
    ) -> PolicyResult:
        del principal
        body: dict[str, Any] = {
            "payload": payload,
            "evidence": evidence,
        }
        if approval is not None:
            body["approval"] = approval
        try:
            response = self._client.post("/v1/evaluate", json=body)
        except httpx.HTTPError as exc:
            raise PeerUnavailableError("policy") from exc
        self._raise(response)
        data = response.json()
        if not isinstance(data, dict) or "outcome" not in data:
            raise PeerError("MALFORMED_PEER", "Malformed policy response", status_code=502)
        return PolicyResult.model_validate(data)

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

    def create_proposal(self, principal: Principal, request: ProposalRequest) -> ActionRecord:
        del principal
        try:
            response = self._client.post(
                "/v1/actions/proposals",
                json={
                    "operation_key": request.operation_key,
                    "payload": request.payload,
                    "action_digest": request.action_digest,
                },
            )
        except httpx.HTTPError as exc:
            raise PeerUnavailableError("action-ledger") from exc
        self._raise(response)
        return self._parse_action(response.json())

    def reserve(self, principal: Principal, request: ReservationRequest) -> ActionRecord:
        del principal
        try:
            response = self._client.post(
                "/v1/actions/reservations",
                json={
                    "operation_key": request.operation_key,
                    "payload": request.payload,
                    "action_digest": request.action_digest,
                    "approval_id": request.approval_id,
                },
            )
        except httpx.HTTPError as exc:
            raise PeerUnavailableError("action-ledger") from exc
        self._raise(response)
        return self._parse_action(response.json())

    def get_action(self, principal: Principal, action_id: str) -> ActionRecord:
        del principal
        try:
            response = self._client.get(f"/v1/actions/{action_id}")
        except httpx.HTTPError as exc:
            raise PeerUnavailableError("action-ledger") from exc
        self._raise(response)
        return self._parse_action(response.json())

    def _parse_action(self, data: Any) -> ActionRecord:
        if not isinstance(data, dict) or "action_id" not in data or "status" not in data:
            raise PeerError("MALFORMED_PEER", "Malformed ledger response", status_code=502)
        return ActionRecord.model_validate(
            {
                "action_id": data["action_id"],
                "provider_ref": data.get("provider_ref") or "",
                "payload": data.get("payload") or {},
                "action_digest": data.get("action_digest") or "",
                "status": data["status"],
                "approval_id": data.get("approval_id"),
            }
        )

    def _raise(self, response: httpx.Response) -> None:
        if response.status_code >= 400:
            code, message = _error_fields(response)
            raise PeerError(code, message, status_code=response.status_code)
