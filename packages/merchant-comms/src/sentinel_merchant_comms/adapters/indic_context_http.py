"""Real-peer HTTP adapter for optional indic-context.v1.

Models propose text only. Failures stay visible to the service, which may fall
back to labeled fake templates because this peer is optional.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from sentinel_merchant_comms.application.errors import (
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_merchant_comms.domain.types import Case, Language, ModelRequest, Principal

PEER = "indic-context.v1"


@dataclass(frozen=True)
class IndicDraftResult:
    body: str
    evidence_mode: str


class IndicContextHttpClient:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("indic-context base_url required when configured")
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._client = httpx.Client(timeout=timeout, transport=transport)

    def close(self) -> None:
        self._client.close()

    def draft_status(
        self, *, case: Case, language: Language, principal: Principal
    ) -> IndicDraftResult:
        _ = principal
        request = _model_request_from_case(case, language)
        url = f"{self._base_url}/v1/proposals"
        try:
            response = self._client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
                json=request.model_dump(exclude_none=True),
            )
        except httpx.HTTPError as exc:
            raise PeerUnavailableError(PEER, "indic-context peer not reachable") from exc

        if response.status_code in {401, 403, 404}:
            raise PeerUnauthorizedError(PEER, "indic principal denied")
        if response.status_code >= 500:
            raise PeerUnavailableError(PEER, f"indic-context returned {response.status_code}")
        if response.status_code != 200:
            raise PeerMalformedError(PEER, f"unexpected status {response.status_code}")

        try:
            payload: dict[str, Any] = response.json()
        except Exception as exc:
            raise PeerMalformedError(PEER, "non-JSON response") from exc

        if "outcome" not in payload or "reason_codes" not in payload:
            raise PeerMalformedError(PEER, "missing ModelResult fields")

        report = payload.get("inference_report") or {}
        evidence_mode = str(report.get("evidence_mode") or "provider-observation")
        body = _status_body_from_model_result(payload, case=case, language=language)
        return IndicDraftResult(body=body, evidence_mode=evidence_mode)


def _model_request_from_case(case: Case, language: Language) -> ModelRequest:
    lang_tag = {"en": "en-IN", "ta": "ta-IN", "hi": "hi-IN"}[language]
    return ModelRequest.model_validate(
        {
            "case": case.model_dump(exclude_none=True),
            "input": {
                "case_id": case.case_id,
                "case_revision": case.revision,
                "original_text": f"Please draft a merchant status update in {language}.",
                "language": lang_tag,
                "order_reference": "DEMO-ORDER-42",
                "messages": [
                    {
                        "message_id": "msg-status-1",
                        "text": f"Status for {case.case_id} is {case.status}",
                        "language": lang_tag,
                        "author": "OPERATOR",
                        "occurred_at": "2026-11-13T12:00:00Z",
                    }
                ],
            },
            "evidence": [],
        }
    )


def _status_body_from_model_result(
    payload: dict[str, Any], *, case: Case, language: Language
) -> str:
    outcome = payload.get("outcome")
    codes = ",".join(payload.get("reason_codes") or [])
    proposal = payload.get("proposal") or {}
    action = proposal.get("action") if isinstance(proposal, dict) else None
    return (
        f"[{language}] Case {case.case_id} status {case.status}. "
        f"Model outcome={outcome} action={action or 'none'} reasons={codes or 'none'}."
    )
