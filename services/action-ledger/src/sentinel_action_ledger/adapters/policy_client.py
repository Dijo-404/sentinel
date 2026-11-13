"""policy.v1 real-peer HTTP adapter — fails closed; never falls back to fixtures."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

from sentinel_action_ledger.adapters.network_guard import ReservationNetworkGuard
from sentinel_action_ledger.application.ports import EvidenceItem
from sentinel_action_ledger.domain.errors import PeerUnavailableError, ValidationError
from sentinel_action_ledger.domain.types import Approval, Principal


class HttpPolicyClient:
    def __init__(
        self,
        base_url: str,
        *,
        token: str,
        guard: ReservationNetworkGuard | None = None,
        timeout: float = 5.0,
    ) -> None:
        if not base_url:
            raise PeerUnavailableError("POLICY_BASE_URL missing for real-peers mode")
        self._base = base_url.rstrip("/")
        self._token = token
        self._guard = guard
        self._timeout = timeout

    def evaluate(
        self,
        *,
        principal: Principal,
        payload: dict[str, Any],
        evidence: Sequence[EvidenceItem],
        approval: Approval | None = None,
    ) -> dict[str, Any]:
        if self._guard is not None:
            self._guard.note_network()
        body: dict[str, Any] = {
            "payload": payload,
            "evidence": [_evidence_dict(item) for item in evidence],
        }
        if approval is not None:
            body["approval"] = {
                "approval_id": approval.approval_id,
                "action_digest": approval.action_digest,
                "case_revision": approval.case_revision,
                "policy_version": approval.policy_version,
                "decision": approval.decision,
                "reviewer_id": approval.reviewer_id,
                "expires_at": approval.expires_at,
            }
        try:
            response = httpx.post(
                f"{self._base}/v1/evaluate",
                json=body,
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise PeerUnavailableError("policy.v1 unavailable") from exc
        if response.status_code >= 500:
            raise PeerUnavailableError("policy.v1 unavailable")
        if response.status_code >= 400:
            raise ValidationError("policy.v1 rejected request", code="PEER_REJECTED")
        data = response.json()
        if not isinstance(data, dict) or "outcome" not in data:
            raise PeerUnavailableError("policy.v1 malformed response")
        return data


def _evidence_dict(item: EvidenceItem) -> dict[str, Any]:
    return {
        "evidence_id": item.evidence_id,
        "case_id": item.case_id,
        "source": item.source,
        "subject_ref": item.subject_ref,
        "observed_at": item.observed_at,
        "expires_at": item.expires_at,
        "digest": item.digest,
        "verification_status": item.verification_status,
        "facts": item.facts,
    }
