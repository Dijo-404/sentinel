"""Real-peer evidence.v1 HTTP adapter. Fail closed; never fall back to fixtures."""

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
from ..domain.types import Principal, RefundFact


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

    def list_refund_facts(
        self,
        principal: Principal,
        *,
        case_ids: list[str],
    ) -> list[RefundFact]:
        del principal
        rows: list[RefundFact] = []
        for case_id in case_ids:
            body = self._get_json(f"/v1/cases/{case_id}/evidence")
            try:
                evidence = body["evidence"]
                if not isinstance(evidence, list):
                    raise TypeError("evidence must be a list")
                for item in evidence:
                    fact = item.get("facts") or {}
                    if fact.get("kind") != "REFUND":
                        continue
                    refund = fact["refund"]
                    rows.append(
                        RefundFact(
                            case_id=case_id,
                            amount_minor=int(refund["amount_minor"]),
                            currency=refund["currency"],
                            status=refund["status"],
                            observed_at=str(item["observed_at"]),
                        )
                    )
            except (KeyError, TypeError, ValueError) as exc:
                raise PeerMalformedError("Evidence peer response failed schema validation") from exc
        return rows

    def _get_json(self, path: str) -> Any:
        try:
            response = self._client.get(
                f"{self._base}{path}",
                headers={"Authorization": f"Bearer {self._token}"},
            )
        except httpx.HTTPError as exc:
            raise PeerUnavailableError("Required peer unavailable") from exc
        if response.status_code in {401, 403}:
            raise PeerUnauthorizedError("Evidence peer denied scoped read")
        if response.status_code >= 500:
            raise PeerUnavailableError("Required peer unavailable")
        if response.status_code == 404:
            return {"contract_version": "sentinel.task-contracts.v1", "case_id": "", "evidence": []}
        if response.status_code != 200:
            raise PeerMalformedError("Evidence peer returned unexpected status")
        try:
            return json.loads(response.content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PeerMalformedError("Evidence peer response was not valid JSON") from exc
