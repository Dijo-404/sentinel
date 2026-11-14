"""Real-peer case-api.v1 HTTP adapter. Fail closed; never fall back to fixtures."""

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
from ..domain.types import CaseRecord, Principal


class HttpCaseApi:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.Client | None = None,
    ) -> None:
        if not base_url.strip():
            raise ConfigurationError("CASE_API_BASE_URL is required in real-peers mode")
        if not token.strip():
            raise ConfigurationError("CASE_API_TOKEN is required in real-peers mode")
        self._base = base_url.rstrip("/")
        self._token = token
        self._client = client or httpx.Client(timeout=10.0)

    def list_merchant_cases(
        self,
        principal: Principal,
        *,
        merchant_ref: str,
        window_start: str,
        window_end: str,
    ) -> list[CaseRecord]:
        del principal, window_start, window_end
        # case-api.v1 ops list is status/cursor scoped; merchant/window filter is local.
        body = self._get_json("/v1/ops/cases", params={})
        try:
            cases_raw = body["cases"]
            if not isinstance(cases_raw, list):
                raise TypeError("cases must be a list")
            rows: list[CaseRecord] = []
            for item in cases_raw:
                if not isinstance(item, dict):
                    raise TypeError("case item must be an object")
                rows.append(_parse_case(item, default_merchant=merchant_ref))
            return rows
        except (KeyError, TypeError, ValueError) as exc:
            raise PeerMalformedError("Case peer response failed schema validation") from exc

    def _get_json(self, path: str, *, params: dict[str, str]) -> Any:
        try:
            response = self._client.get(
                f"{self._base}{path}",
                params=params,
                headers={"Authorization": f"Bearer {self._token}"},
            )
        except httpx.HTTPError as exc:
            raise PeerUnavailableError("Required peer unavailable") from exc
        if response.status_code in {401, 403}:
            raise PeerUnauthorizedError("Case peer denied scoped read")
        if response.status_code >= 500:
            raise PeerUnavailableError("Required peer unavailable")
        if response.status_code != 200:
            raise PeerMalformedError("Case peer returned unexpected status")
        try:
            return json.loads(response.content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PeerMalformedError("Case peer response was not valid JSON") from exc


def _parse_case(item: dict[str, Any], *, default_merchant: str) -> CaseRecord:
    """Map case-api.v1 Case (+ optional analytics fields). Missing required fields fail closed."""
    case_id = item["case_id"]
    status = item["status"]
    intent = item["intent"]
    if not isinstance(case_id, str) or not case_id:
        raise TypeError("case_id")
    if not isinstance(status, str) or not status:
        raise TypeError("status")
    if not isinstance(intent, str) or not intent:
        raise TypeError("intent")

    evidence_ids = item["evidence_ids"]
    if not isinstance(evidence_ids, list) or not all(isinstance(x, str) for x in evidence_ids):
        raise TypeError("evidence_ids")

    # Analytics windowing needs a timestamp. Case wire may omit it → fail closed.
    opened_at = item.get("opened_at")
    if opened_at is None:
        opened_at = item.get("created_at")
    if not isinstance(opened_at, str) or not opened_at:
        raise TypeError("opened_at")

    closed_at = item.get("closed_at")
    if closed_at is not None and not isinstance(closed_at, str):
        raise TypeError("closed_at")

    merchant_ref = item.get("merchant_ref")
    if merchant_ref is None:
        merchant_ref = default_merchant
    elif not isinstance(merchant_ref, str) or not merchant_ref:
        raise TypeError("merchant_ref")

    currency = item.get("currency", "INR")
    if currency != "INR":
        raise TypeError("currency")

    return CaseRecord(
        case_id=case_id,
        merchant_ref=merchant_ref,
        status=status,
        intent=intent,
        opened_at=opened_at,
        closed_at=closed_at,
        evidence_ids=tuple(evidence_ids),
        currency="INR",
    )
