"""evidence.v1 real-peer HTTP adapter — fails closed."""

from __future__ import annotations

from collections.abc import Sequence

import httpx

from sentinel_action_ledger.adapters.network_guard import ReservationNetworkGuard
from sentinel_action_ledger.application.ports import EvidenceItem
from sentinel_action_ledger.domain.errors import PeerUnavailableError, ValidationError
from sentinel_action_ledger.domain.types import Principal


class HttpEvidenceClient:
    def __init__(
        self,
        base_url: str,
        *,
        token: str,
        guard: ReservationNetworkGuard | None = None,
        timeout: float = 5.0,
    ) -> None:
        if not base_url:
            raise PeerUnavailableError("EVIDENCE_BASE_URL missing for real-peers mode")
        self._base = base_url.rstrip("/")
        self._token = token
        self._guard = guard
        self._timeout = timeout

    def collect(
        self, *, principal: Principal, case_id: str, case_revision: int, order_reference: str
    ) -> Sequence[EvidenceItem]:
        if self._guard is not None:
            self._guard.note_network()
        try:
            response = httpx.post(
                f"{self._base}/v1/evidence/collect",
                json={
                    "case_id": case_id,
                    "case_revision": case_revision,
                    "order_reference": order_reference,
                },
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise PeerUnavailableError("evidence.v1 unavailable") from exc
        if response.status_code >= 500:
            raise PeerUnavailableError("evidence.v1 unavailable")
        if response.status_code >= 400:
            raise ValidationError("evidence.v1 rejected request", code="PEER_REJECTED")
        data = response.json()
        if not isinstance(data, dict) or "evidence" not in data:
            raise PeerUnavailableError("evidence.v1 malformed response")
        items: list[EvidenceItem] = []
        for raw in data["evidence"]:
            items.append(
                EvidenceItem(
                    evidence_id=raw["evidence_id"],
                    case_id=raw["case_id"],
                    source=raw["source"],
                    subject_ref=raw["subject_ref"],
                    observed_at=raw["observed_at"],
                    expires_at=raw["expires_at"],
                    digest=raw["digest"],
                    verification_status=raw["verification_status"],
                    facts=raw["facts"],
                )
            )
        return items
