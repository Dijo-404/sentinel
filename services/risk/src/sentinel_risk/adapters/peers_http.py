"""HTTP peers for case-api and workflow. Fail closed; never fall back to fixtures."""

from __future__ import annotations

import httpx

from ..application.errors import (
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from ..domain.types import CONTRACT_VERSION, CaseSnapshot, Principal, ResumeEvent


class HttpCaseApi:
    def __init__(self, base_url: str, token: str, *, client: httpx.Client | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._client = client or httpx.Client(timeout=10.0)

    def get_case(self, case_id: str, *, principal: Principal) -> CaseSnapshot:
        del principal
        try:
            response = self._client.get(
                f"{self._base_url}/v1/cases/{case_id}",
                headers={"Authorization": f"Bearer {self._token}"},
            )
        except httpx.HTTPError as exc:
            raise PeerUnavailableError("case-api unavailable") from exc
        if response.status_code in {401, 403}:
            raise PeerUnauthorizedError("case-api unauthorized or out of scope")
        if response.status_code >= 500:
            raise PeerUnavailableError("case-api unavailable")
        if response.status_code != 200:
            raise PeerMalformedError(f"case-api unexpected status {response.status_code}")
        try:
            body = response.json()
        except ValueError as exc:
            raise PeerMalformedError("case-api returned non-JSON") from exc
        if not isinstance(body, dict) or "case_id" not in body:
            raise PeerMalformedError("case-api returned malformed Case")
        return CaseSnapshot(
            contract_version=str(body.get("contract_version", CONTRACT_VERSION)),
            case_id=str(body["case_id"]),
            revision=int(body.get("revision", 1)),
            status=str(body.get("status", "")),
            language=str(body.get("language", "")),
            intent=str(body.get("intent", "")),
            evidence_ids=tuple(str(x) for x in body.get("evidence_ids", [])),
            escalation_destination=(
                str(body["escalation_destination"])
                if body.get("escalation_destination") is not None
                else None
            ),
        )


class HttpWorkflow:
    def __init__(self, base_url: str, token: str, *, client: httpx.Client | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._client = client or httpx.Client(timeout=10.0)

    def emit_resume(self, event: ResumeEvent, *, principal: Principal) -> None:
        del principal
        if event.financial_approval_granted:
            raise PeerMalformedError("refuse resume event with financial_approval_granted")
        payload = {
            "event_type": event.event_type,
            "investigation_id": event.investigation_id,
            "case_id": event.case_id,
            "restriction_id": event.restriction_id,
            "tenant_id": event.tenant_id,
            "financial_approval_granted": False,
        }
        try:
            response = self._client.post(
                f"{self._base_url}/v1/workflow/risk-resume",
                headers={"Authorization": f"Bearer {self._token}"},
                json=payload,
            )
        except httpx.HTTPError as exc:
            raise PeerUnavailableError("workflow unavailable") from exc
        if response.status_code in {401, 403}:
            raise PeerUnauthorizedError("workflow unauthorized or out of scope")
        if response.status_code >= 500:
            raise PeerUnavailableError("workflow unavailable")
        if response.status_code not in {200, 202, 204}:
            raise PeerMalformedError(f"workflow unexpected status {response.status_code}")
