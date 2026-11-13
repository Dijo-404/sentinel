"""Real-peer HTTP adapters. Never silently fall back to fixtures."""

from __future__ import annotations

from typing import Any

import httpx

from sentinel_workflow.application.errors import PeerError, PeerUnavailableError
from sentinel_workflow.domain.types import (
    ActionRecord,
    Case,
    CaseInput,
    CaseResult,
    EvidenceBundle,
    PolicyRequest,
    PolicyResult,
    ProposalRequest,
    ReservationRequest,
    VerificationRequest,
    VerificationResult,
)


def _client(base_url: str, token: str, timeout: float = 10.0) -> tuple[str, dict[str, str], float]:
    if not base_url:
        raise PeerUnavailableError("peer")
    return base_url.rstrip("/"), {"Authorization": f"Bearer {token}"}, timeout


def _request(
    method: str,
    url: str,
    headers: dict[str, str],
    *,
    peer: str,
    json: dict[str, Any] | None = None,
    timeout: float = 10.0,
    extra_headers: dict[str, str] | None = None,
) -> httpx.Response:
    hdrs = dict(headers)
    if extra_headers:
        hdrs.update(extra_headers)
    try:
        response = httpx.request(method, url, headers=hdrs, json=json, timeout=timeout)
    except httpx.HTTPError as exc:
        raise PeerUnavailableError(peer) from exc
    if response.status_code >= 500:
        raise PeerUnavailableError(peer)
    if response.status_code in {401, 403}:
        raise PeerError("UNAUTHORIZED", f"{peer} unauthorized or out of scope", 403)
    if response.status_code == 404:
        raise PeerError("NOT_FOUND", f"{peer} resource not found", 404)
    if response.status_code == 409:
        code = "CONFLICT"
        message = f"{peer} conflict"
        try:
            body = response.json()
        except Exception:
            body = None
        if isinstance(body, dict):
            if body.get("code"):
                code = str(body["code"])
            if body.get("message"):
                message = str(body["message"])
        raise PeerError(code, message, 409)
    if response.status_code >= 400:
        code = "PEER_ERROR"
        message = f"{peer} returned {response.status_code}"
        try:
            body = response.json()
        except Exception:
            body = None
        if isinstance(body, dict) and body.get("code"):
            code = str(body["code"])
        raise PeerError(code, message, 502)
    return response


class HttpCaseApi:
    def __init__(self, base_url: str, token: str) -> None:
        self._base, self._headers, self._timeout = _client(base_url, token)

    def get_input(self, case_id: str, revision: int) -> CaseInput:
        response = _request(
            "GET",
            f"{self._base}/v1/internal/cases/{case_id}/input?revision={revision}",
            self._headers,
            peer="case-api",
            timeout=self._timeout,
        )
        try:
            return CaseInput.model_validate(response.json())
        except Exception as exc:
            raise PeerError("MALFORMED", "case-api returned malformed CaseInput", 502) from exc

    def get_case(self, case_id: str) -> Case:
        response = _request(
            "GET",
            f"{self._base}/v1/cases/{case_id}",
            self._headers,
            peer="case-api",
            timeout=self._timeout,
        )
        try:
            return Case.model_validate(response.json())
        except Exception as exc:
            raise PeerError("MALFORMED", "case-api returned malformed Case", 502) from exc

    def submit_result(self, case_id: str, result: CaseResult) -> Case:
        response = _request(
            "POST",
            f"{self._base}/v1/internal/cases/{case_id}/results",
            self._headers,
            peer="case-api",
            json=result.model_dump(exclude_none=True),
            timeout=self._timeout,
        )
        try:
            return Case.model_validate(response.json())
        except Exception as exc:
            raise PeerError("MALFORMED", "case-api returned malformed Case", 502) from exc


class HttpEvidence:
    def __init__(self, base_url: str, token: str) -> None:
        self._base, self._headers, self._timeout = _client(base_url, token)

    def collect(self, case_id: str, case_revision: int, order_reference: str) -> EvidenceBundle:
        response = _request(
            "POST",
            f"{self._base}/v1/evidence/collect",
            self._headers,
            peer="evidence",
            json={
                "case_id": case_id,
                "case_revision": case_revision,
                "order_reference": order_reference,
            },
            timeout=self._timeout,
        )
        try:
            return EvidenceBundle.model_validate(response.json())
        except Exception as exc:
            raise PeerError("MALFORMED", "evidence returned malformed bundle", 502) from exc


class HttpPolicy:
    def __init__(self, base_url: str, token: str) -> None:
        self._base, self._headers, self._timeout = _client(base_url, token)

    def evaluate(self, request: PolicyRequest) -> PolicyResult:
        body = request.model_dump(exclude_none=True)
        response = _request(
            "POST",
            f"{self._base}/v1/evaluate",
            self._headers,
            peer="policy",
            json=body,
            timeout=self._timeout,
        )
        try:
            return PolicyResult.model_validate(response.json())
        except Exception as exc:
            raise PeerError("MALFORMED", "policy returned malformed result", 502) from exc


class HttpLedger:
    def __init__(self, base_url: str, token: str) -> None:
        self._base, self._headers, self._timeout = _client(base_url, token)

    def create_proposal(self, request: ProposalRequest) -> ActionRecord:
        response = _request(
            "POST",
            f"{self._base}/v1/actions/proposals",
            self._headers,
            peer="action-ledger",
            json=request.model_dump(exclude_none=True),
            timeout=self._timeout,
        )
        try:
            return ActionRecord.model_validate(response.json())
        except Exception as exc:
            raise PeerError("MALFORMED", "ledger returned malformed ActionRecord", 502) from exc

    def reserve(self, request: ReservationRequest) -> ActionRecord:
        response = _request(
            "POST",
            f"{self._base}/v1/actions/reservations",
            self._headers,
            peer="action-ledger",
            json=request.model_dump(exclude_none=True),
            timeout=self._timeout,
        )
        try:
            return ActionRecord.model_validate(response.json())
        except Exception as exc:
            raise PeerError("MALFORMED", "ledger returned malformed ActionRecord", 502) from exc

    def get_action(self, action_id: str) -> ActionRecord:
        response = _request(
            "GET",
            f"{self._base}/v1/actions/{action_id}",
            self._headers,
            peer="action-ledger",
            timeout=self._timeout,
        )
        try:
            return ActionRecord.model_validate(response.json())
        except Exception as exc:
            raise PeerError("MALFORMED", "ledger returned malformed ActionRecord", 502) from exc


class HttpVerifier:
    def __init__(self, base_url: str, token: str) -> None:
        self._base, self._headers, self._timeout = _client(base_url, token)

    def schedule_recheck(self, request: VerificationRequest, idempotency_key: str) -> str:
        response = _request(
            "POST",
            f"{self._base}/v1/rechecks",
            self._headers,
            peer="verifier",
            json=request.model_dump(exclude_none=True),
            timeout=self._timeout,
            extra_headers={"Idempotency-Key": idempotency_key},
        )
        body = response.json()
        return str(body.get("job_id") or idempotency_key)

    def assess(self, request: VerificationRequest) -> VerificationResult:
        response = _request(
            "POST",
            f"{self._base}/v1/assessments",
            self._headers,
            peer="verifier",
            json=request.model_dump(exclude_none=True),
            timeout=self._timeout,
        )
        try:
            return VerificationResult.model_validate(response.json())
        except Exception as exc:
            raise PeerError("MALFORMED", "verifier returned malformed assessment", 502) from exc
