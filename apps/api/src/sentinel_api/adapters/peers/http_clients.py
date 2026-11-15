"""Real-peer HTTP adapters. Reject unavailable/malformed/unauthorized peers."""

from __future__ import annotations

from typing import Any

import httpx

from sentinel_api.adapters.peers.errors import malformed, rejected, unauthorized, unavailable
from sentinel_api.domain.types import (
    CONTRACT_VERSION,
    Approval,
    DecisionRequest,
    EvidenceBundle,
    VerificationResult,
    WorkflowRequest,
)


class HttpWorkflowClient:
    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        if not base_url:
            raise ValueError("workflow base_url required in real-peers mode")
        self._base = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=5.0)

    def start_run(self, request: WorkflowRequest, *, authorization: str) -> None:
        try:
            response = self._client.post(
                f"{self._base}/v1/runs",
                json=request.to_wire_dict(),
                headers={"Authorization": authorization},
            )
        except httpx.HTTPError as exc:
            raise unavailable("workflow") from exc
        if response.status_code in {409, 422, 429}:
            raise rejected("workflow", response.status_code)
        self._check("workflow", response)
        body = response.json()
        if not isinstance(body, dict) or body.get("accepted") is not True:
            raise malformed("workflow")


class HttpEvidenceClient:
    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        if not base_url:
            raise ValueError("evidence base_url required in real-peers mode")
        self._base = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=5.0)

    def get_case_evidence(self, case_id: str, *, authorization: str) -> EvidenceBundle:
        try:
            response = self._client.get(
                f"{self._base}/v1/cases/{case_id}/evidence",
                headers={"Authorization": authorization},
            )
        except httpx.HTTPError as exc:
            raise unavailable("evidence") from exc
        self._check("evidence", response)
        body = response.json()
        try:
            return EvidenceBundle(
                contract_version=body["contract_version"],
                case_id=body["case_id"],
                evidence=tuple(body["evidence"]),
                reconciliation_codes=tuple(body.get("reconciliation_codes", [])),
            )
        except (KeyError, TypeError) as exc:
            raise malformed("evidence") from exc

    @staticmethod
    def _check(peer: str, response: httpx.Response) -> None:
        if response.status_code in {401, 403}:
            raise unauthorized(peer)
        if response.status_code >= 500:
            raise unavailable(peer)
        if response.status_code >= 400:
            raise malformed(peer)


# Bind shared checker onto workflow client
HttpWorkflowClient._check = staticmethod(HttpEvidenceClient._check)  # type: ignore[attr-defined]


class HttpLedgerClient:
    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        if not base_url:
            raise ValueError("ledger base_url required in real-peers mode")
        self._base = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=5.0)

    def decide(self, action_id: str, request: DecisionRequest, *, authorization: str) -> Approval:
        try:
            response = self._client.post(
                f"{self._base}/v1/actions/{action_id}/decisions",
                json=request.to_dict(),
                headers={"Authorization": authorization},
            )
        except httpx.HTTPError as exc:
            raise unavailable("action-ledger") from exc
        HttpEvidenceClient._check("action-ledger", response)
        body = response.json()
        try:
            return Approval(
                approval_id=body["approval_id"],
                action_digest=body["action_digest"],
                case_revision=body["case_revision"],
                policy_version=body["policy_version"],
                decision=body["decision"],
                reviewer_id=body["reviewer_id"],
                expires_at=body["expires_at"],
            )
        except (KeyError, TypeError) as exc:
            raise malformed("action-ledger") from exc


class HttpVerifierClient:
    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        if not base_url:
            raise ValueError("verifier base_url required in real-peers mode")
        self._base = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=5.0)

    def get_assessment(self, assessment_id: str, *, authorization: str) -> VerificationResult:
        try:
            response = self._client.get(
                f"{self._base}/v1/assessments/{assessment_id}",
                headers={"Authorization": authorization},
            )
        except httpx.HTTPError as exc:
            raise unavailable("verifier") from exc
        HttpEvidenceClient._check("verifier", response)
        body = response.json()
        try:
            return VerificationResult(
                assessment_id=body["assessment_id"],
                case_id=body["case_id"],
                case_revision=body["case_revision"],
                action_id=body["action_id"],
                assessed_at=body["assessed_at"],
                expires_at=body["expires_at"],
                status=body["status"],
                evidence=tuple(body["evidence"]),
                reason_codes=tuple(body.get("reason_codes", [])),
            )
        except (KeyError, TypeError) as exc:
            raise malformed("verifier") from exc


def parse_approval(body: dict[str, Any]) -> Approval:
    return Approval(
        approval_id=body["approval_id"],
        action_digest=body["action_digest"],
        case_revision=body["case_revision"],
        policy_version=body["policy_version"],
        decision=body["decision"],
        reviewer_id=body["reviewer_id"],
        expires_at=body["expires_at"],
    )


def empty_evidence(case_id: str) -> EvidenceBundle:
    return EvidenceBundle(
        contract_version=CONTRACT_VERSION,
        case_id=case_id,
        evidence=(),
        reconciliation_codes=(),
    )
