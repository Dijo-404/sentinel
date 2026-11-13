"""Real-peer evidence.v1 HTTP adapter. Fail closed; never fall back to fixtures."""

from __future__ import annotations

import json
from typing import Any

import httpx

from sentinel_merchant_settlement.application.errors import (
    ConfigurationError,
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_merchant_settlement.domain.types import EvidenceRecord, PeerWorld, Principal


class HttpEvidence:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.Client | None = None,
    ) -> None:
        if not base_url.strip():
            raise ConfigurationError("EVIDENCE_BASE_URL is required in real-peers mode")
        if not token.strip():
            raise ConfigurationError("EVIDENCE_TOKEN is required in real-peers mode")
        self._base = base_url.rstrip("/")
        self._token = token
        self._client = client or httpx.Client(timeout=10.0)

    def load_world(
        self,
        *,
        principal: Principal,
        tenant_id: str,
        merchant_ref: str,
        order_refs: tuple[str, ...],
        transaction_refs: tuple[str, ...],
    ) -> PeerWorld:
        del principal, tenant_id, merchant_ref, transaction_refs
        records: list[EvidenceRecord] = []
        for order_reference in order_refs:
            body = self._post_json(
                "/v1/evidence/collect",
                {
                    "case_id": f"case-for-{order_reference}",
                    "case_revision": 1,
                    "order_reference": order_reference,
                },
            )
            try:
                for item in body["evidence"]:
                    records.append(_parse_evidence(item))
            except (KeyError, TypeError, ValueError) as exc:
                raise PeerMalformedError("Evidence response failed schema validation") from exc
        return PeerWorld(payments=(), orders=(), evidence=tuple(records))

    def _post_json(self, path: str, payload: dict) -> Any:
        try:
            response = self._client.post(
                f"{self._base}{path}",
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
                content=json.dumps(payload).encode("utf-8"),
            )
        except httpx.HTTPError as exc:
            raise PeerUnavailableError("Required peer unavailable") from exc
        if response.status_code in {401, 403}:
            raise PeerUnauthorizedError("Evidence denied scoped read")
        if response.status_code >= 500:
            raise PeerUnavailableError("Required peer unavailable")
        if response.status_code != 200:
            raise PeerMalformedError("Evidence returned unexpected status")
        try:
            return json.loads(response.content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PeerMalformedError("Evidence response was not valid JSON") from exc


def _parse_evidence(item: dict) -> EvidenceRecord:
    facts = item.get("facts") or {}
    txn = None
    order = None
    if facts.get("kind") == "PAYMENT":
        txn = str(facts["payment"]["transaction_ref"])
        order = str(facts["payment"].get("order_reference") or "") or None
    elif facts.get("kind") == "ORDER":
        order = str(facts["order"]["order_reference"])
    return EvidenceRecord(
        evidence_id=str(item["evidence_id"]),
        transaction_ref=txn,
        order_reference=order,
        verification_status=str(item["verification_status"]),
    )
